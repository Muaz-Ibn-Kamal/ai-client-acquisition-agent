import httpx
import pytest

from app.api.pipeline import get_fetcher
from app.core.config import get_settings
from app.main import app
from app.services.discovery.base import ProviderUnavailableError
from app.services.discovery.providers import CsvProvider, GooglePlacesProvider
from tests.helpers import BAD_HTML, GOOD_HTML, make_fetcher

CSV = """name,website,industry,country,location
Acme Plumbing,https://www.acme.com,Plumbing,USA,Austin
Acme Again,http://acme.com/about,,,
Bad Row,,,,
Local,http://127.0.0.1,,,
"""


async def test_csv_provider_parses_and_skips_incomplete_rows() -> None:
    found = await CsvProvider(CSV).discover(None, 10)
    assert [c.name for c in found] == ["Acme Plumbing", "Acme Again", "Local"]
    assert found[0].country == "USA"
    assert len(await CsvProvider(CSV).discover(None, 1)) == 1


async def test_places_provider_requires_key(monkeypatch) -> None:
    monkeypatch.setattr(get_settings(), "google_places_api_key", None)
    with pytest.raises(ProviderUnavailableError):
        await GooglePlacesProvider().discover("dentists", 5)


async def test_places_provider_parses_mocked_response(monkeypatch) -> None:
    monkeypatch.setattr(get_settings(), "google_places_api_key", "test-key")
    captured: dict = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["key"] = request.headers["x-goog-api-key"]
        captured["mask"] = request.headers["x-goog-fieldmask"]
        return httpx.Response(
            200,
            json={
                "places": [
                    {
                        "displayName": {"text": "Smile Dental"},
                        "websiteUri": "https://smile.example",
                        "formattedAddress": "1 Main St",
                        "primaryTypeDisplayName": {"text": "Dentist"},
                    },
                    {"displayName": {"text": "No Site Clinic"}},
                ]
            },
        )  # fmt: skip

    provider = GooglePlacesProvider(transport=httpx.MockTransport(handler))
    found = await provider.discover("dentists toronto", 10)
    assert [c.name for c in found] == ["Smile Dental"]
    assert captured["key"] == "test-key" and "websiteUri" in captured["mask"]


async def test_places_provider_http_error_is_unavailable(monkeypatch) -> None:
    monkeypatch.setattr(get_settings(), "google_places_api_key", "k")
    provider = GooglePlacesProvider(
        transport=httpx.MockTransport(lambda r: httpx.Response(403, json={}))
    )
    with pytest.raises(ProviderUnavailableError):
        await provider.discover("x", 5)


async def test_discover_endpoint_dedupes_and_creates_leads(api) -> None:
    r = await api.post("/discover", json={"provider": "csv", "csv_text": CSV})
    assert r.status_code == 200, r.text
    body = r.json()
    # Acme + Acme Again share a domain; 127.0.0.1 is invalid.
    assert (body["found"], body["new_companies"], body["duplicates"], body["invalid"]) == (
        3,
        1,
        1,
        1,
    )
    assert len(body["lead_ids"]) == 1
    lead = (await api.get(f"/leads/{body['lead_ids'][0]}")).json()
    assert lead["source_name"] == "csv_import" and lead["company"]["domain"] == "acme.com"

    again = (await api.post("/discover", json={"provider": "csv", "csv_text": CSV})).json()
    assert again["new_companies"] == 0 and again["duplicates"] == 2


async def test_discover_validation_and_unavailable_provider(api, monkeypatch) -> None:
    assert (await api.post("/discover", json={"provider": "csv"})).status_code == 422
    assert (await api.post("/discover", json={"provider": "manual"})).status_code == 422
    assert (await api.post("/discover", json={"provider": "nope"})).status_code == 422
    monkeypatch.setattr(get_settings(), "google_places_api_key", None)
    r = await api.post("/discover", json={"provider": "google_places", "query": "x"})
    assert r.status_code == 503


async def test_discover_manual(api) -> None:
    r = await api.post(
        "/discover",
        json={
            "provider": "manual",
            "companies": [{"name": "X Co", "website": "xco.io", "country": "UK"}],
        },
    )
    assert r.status_code == 200 and r.json()["new_companies"] == 1


def _override_fetcher(html: str, status: int = 200):
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/robots.txt":
            return httpx.Response(404)
        return httpx.Response(status, html=html)

    app.dependency_overrides[get_fetcher] = lambda: make_fetcher(handler)


async def _company_and_lead(api, website="https://acme.com"):
    c = (await api.post("/companies", json={"name": "Acme", "website": website})).json()
    lead = (await api.post("/leads", json={"company_id": c["id"]})).json()
    return c, lead


async def test_research_persists_evidence_contacts_and_opportunities(api) -> None:
    _override_fetcher(BAD_HTML)
    company, lead = await _company_and_lead(api)
    r = await api.post(f"/research/{company['id']}")
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["opportunities_added"] >= 4 and body["contacts_added"] == 0
    assert any(i["code"] == "no_viewport" and i["label"] == "INFERENCE" for i in body["insights"])
    assert (await api.get(f"/leads/{lead['id']}")).json()["status"] == "researched"
    # Re-running replaces opportunities instead of duplicating them.
    again = (await api.post(f"/research/{company['id']}")).json()
    assert again["opportunities_added"] == body["opportunities_added"]


async def test_research_stores_only_company_domain_contacts(api, db_session) -> None:
    _override_fetcher(GOOD_HTML)
    company, _ = await _company_and_lead(api)
    body = (await api.post(f"/research/{company['id']}")).json()
    assert (
        body["contacts_added"] == 3
    )  # info@, jane.doe@ (same domain) and the phone; gmail skipped
    from sqlalchemy import select

    from app.models import Contact

    contacts = (await db_session.execute(select(Contact))).scalars().all()
    assert {c.email for c in contacts if c.email} == {"info@acme.com", "jane.doe@acme.com"}
    for c in contacts:
        assert c.source_attribution.startswith("https://acme.com")
        assert c.data_provenance and c.collected_at and c.is_public_business_contact
    assert (await api.post(f"/research/{company['id']}")).json()["contacts_added"] == 0  # no dupes


async def test_research_errors(api) -> None:
    import uuid

    assert (await api.post(f"/research/{uuid.uuid4()}")).status_code == 404
    _override_fetcher("", status=500)
    company, _ = await _company_and_lead(api)
    assert (await api.post(f"/research/{company['id']}")).status_code == 502
    # Company pointing at an internal host is refused (SSRF), not fetched.
    app.dependency_overrides[get_fetcher] = lambda: make_fetcher(lambda r: httpx.Response(200))
    internal = (await api.post("/companies", json={"name": "I", "website": "internal.test"})).json()
    r = await api.post(f"/research/{internal['id']}")
    assert r.status_code == 502 and "blocked" in r.json()["detail"]


async def test_score_uses_research_and_overrides(api) -> None:
    import uuid

    _override_fetcher(BAD_HTML)
    company, lead = await _company_and_lead(api)
    before = (await api.post(f"/score/{lead['id']}")).json()
    assert before["total_score"] == 0 and before["confidence"] == 0  # nothing researched yet

    await api.post(f"/research/{company['id']}")
    derived = (await api.post(f"/score/{lead['id']}")).json()
    assert derived["total_score"] > 0
    assert derived["opportunity_strength"] > 0 and derived["contactability"] == 0
    assert 0 < derived["confidence"] < 1

    overridden = (
        await api.post(
            f"/score/{lead['id']}",
            json={
                "overrides": {
                    "service_fit": {"needs_match": {"value": 1, "reason": "asked for redesign"}}
                }
            },
        )
    ).json()
    assert overridden["service_fit"] == derived["service_fit"] + 12.5
    assert "asked for redesign" in " ".join(overridden["reasons"]["service_fit"])

    latest = (await api.get(f"/leads/{lead['id']}")).json()["latest_score"]
    assert latest["total_score"] == overridden["total_score"]

    assert (await api.post(f"/score/{uuid.uuid4()}")).status_code == 404
    bad = await api.post(f"/score/{lead['id']}", json={"overrides": {"nope": {}}})
    assert bad.status_code == 422
    bad = await api.post(
        f"/score/{lead['id']}", json={"overrides": {"service_fit": {"x": {"value": 1}}}}
    )
    assert bad.status_code == 422
    bad = await api.post(
        f"/score/{lead['id']}", json={"overrides": {"service_fit": {"needs_match": {"value": 7}}}}
    )
    assert bad.status_code == 422
