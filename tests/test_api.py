import uuid

from sqlalchemy.ext.asyncio import AsyncEngine, async_sessionmaker

from app.repositories import lead as lead_repo
from app.scoring import COMPONENT_FACTORS, FactorSignal, ScoringWeights, score_lead


async def _company(api, name="Acme", website="https://acme.com", **extra):
    r = await api.post("/companies", json={"name": name, "website": website, **extra})
    assert r.status_code in (200, 201), r.text
    return r


async def _lead(api, company_id, **extra):
    r = await api.post("/leads", json={"company_id": company_id, **extra})
    assert r.status_code == 201, r.text
    return r.json()


async def _score(db_engine: AsyncEngine, lead_id: str, value: float) -> None:
    signals = {c: {f: FactorSignal(value) for f in fs} for c, fs in COMPONENT_FACTORS.items()}
    async with async_sessionmaker(db_engine, expire_on_commit=False)() as session:
        lead = await lead_repo.get_lead(session, uuid.UUID(lead_id))
        assert lead is not None
        await lead_repo.save_score(session, lead, score_lead(signals), ScoringWeights())
        await session.commit()


async def test_create_company_deduplicates(api) -> None:
    first = await _company(api, website="https://www.acme.com/")
    second = await _company(api, name="Acme Again", website="http://ACME.com/contact")
    assert first.status_code == 201 and second.status_code == 200
    assert first.json()["id"] == second.json()["id"]
    assert first.json()["domain"] == "acme.com"
    listing = (await api.get("/companies")).json()
    assert listing["total"] == 1


async def test_company_validation_and_404(api) -> None:
    assert (
        await api.post("/companies", json={"name": "X", "website": "http://127.0.0.1"})
    ).status_code == 422
    assert (await api.post("/companies", json={"name": "", "website": "x.com"})).status_code == 422
    assert (await api.get(f"/companies/{uuid.uuid4()}")).status_code == 404
    assert (await api.get("/companies/not-a-uuid")).status_code == 422


async def test_company_filters_and_pagination(api) -> None:
    for i, country in enumerate(["USA", "UK", "USA"]):
        await _company(api, name=f"C{i}", website=f"c{i}.com", country=country)
    assert (await api.get("/companies", params={"country": "usa"})).json()["total"] == 2
    page = (await api.get("/companies", params={"limit": 1, "offset": 1})).json()
    assert page["total"] == 3 and len(page["items"]) == 1


async def test_lead_create_get_and_404s(api) -> None:
    company = (await _company(api)).json()
    lead = await _lead(api, company["id"], source_name="manual", recommended_service="landing_page")
    assert (
        lead["status"] == "new" and lead["source_name"] == "manual" and lead["latest_score"] is None
    )
    got = (await api.get(f"/leads/{lead['id']}")).json()
    assert got["company"]["domain"] == "acme.com"
    assert (await api.get(f"/leads/{uuid.uuid4()}")).status_code == 404
    assert (await api.post("/leads", json={"company_id": str(uuid.uuid4())})).status_code == 404
    bad = await api.post(
        "/leads", json={"company_id": company["id"], "recommended_service": "hacking"}
    )
    assert bad.status_code == 422


async def test_lead_filtering_and_ranking(api, db_engine) -> None:
    specs = [
        ("hi.com", "USA", "web_development", 0.9),
        ("mid.com", "UK", "website_redesign", 0.65),
        ("low.com", "USA", "web_development", 0.2),
        ("unscored.com", "USA", "branding", None),
    ]
    ids = {}
    for domain, country, service, value in specs:
        company = (await _company(api, name=domain, website=domain, country=country)).json()
        lead = await _lead(api, company["id"], recommended_service=service)
        ids[domain] = lead["id"]
        if value is not None:
            await _score(db_engine, lead["id"], value)

    def domains(body):
        return [i["company"]["domain"] for i in body["items"]]

    ranked = (await api.get("/leads")).json()
    assert domains(ranked) == ["hi.com", "mid.com", "low.com", "unscored.com"]  # unscored last
    assert ranked["items"][0]["latest_score"]["total_score"] == 90

    assert domains((await api.get("/leads", params={"min_score": 80})).json()) == ["hi.com"]
    assert domains((await api.get("/leads", params={"min_score": 60})).json()) == [
        "hi.com",
        "mid.com",
    ]
    assert (await api.get("/leads", params={"country": "UK"})).json()["total"] == 1
    assert domains((await api.get("/leads", params={"service": "web_development"})).json()) == [
        "hi.com",
        "low.com",
    ]
    assert (await api.get("/leads", params={"status": "new"})).json()["total"] == 4
    assert (await api.get("/leads", params={"status": "qualified"})).json()["total"] == 0
    assert (await api.get("/leads", params={"status": "bogus"})).status_code == 422
    assert (await api.get("/leads", params={"min_score": 101})).status_code == 422

    page = (await api.get("/leads", params={"limit": 2, "offset": 2})).json()
    assert page["total"] == 4 and domains(page) == ["low.com", "unscored.com"]


async def test_latest_score_wins_when_rescored(api, db_engine) -> None:
    company = (await _company(api)).json()
    lead = await _lead(api, company["id"])
    await _score(db_engine, lead["id"], 0.2)
    await _score(db_engine, lead["id"], 0.9)
    assert (await api.get(f"/leads/{lead['id']}")).json()["latest_score"]["total_score"] == 90
    assert (await api.get("/leads", params={"min_score": 80})).json()["total"] == 1


async def test_no_outreach_endpoints_exist(api) -> None:
    for path in ("/send", "/outreach", "/messages", "/proposals"):
        assert (await api.post(path)).status_code == 404
