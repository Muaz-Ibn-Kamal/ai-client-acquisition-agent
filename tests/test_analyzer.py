from app.scrapers.analyzer import Insight, analyze_html
from tests.helpers import BAD_HTML, GOOD_HTML


def test_good_page_signals() -> None:
    s = analyze_html(GOOD_HTML, "https://acme.com/")
    assert s.title == "Acme Plumbing"
    assert s.meta_description == "Plumbers in Austin"
    assert s.has_viewport_meta and s.uses_https and s.has_cta
    assert s.headings == ["Acme Plumbing", "Our services"]
    assert s.nav_links == ["Home", "Services"]
    assert "WordPress" in s.technologies
    emails = {c.email: c.contact_type for c in s.contacts if c.email}
    assert emails["info@acme.com"] == "business_inbox"
    assert emails["jane.doe@acme.com"] == "named_individual"
    assert any(c.phone == "+15125550100" for c in s.contacts)
    assert {i.code for i in s.insights} == {"technologies"}  # no problems on a healthy page


def test_problem_page_produces_evidence_backed_insights() -> None:
    s = analyze_html(BAD_HTML, "http://bad.example.com/")
    codes = {i.code for i in s.insights}
    assert {"no_https", "no_viewport", "no_title", "no_meta_description", "no_cta",
            "images_missing_alt", "no_contacts"} <= codes  # fmt: skip
    for insight in s.insights:
        assert insight.evidence and insight.source_url == "http://bad.example.com/"
        assert insight.label in ("FACT", "INFERENCE", "UNKNOWN")
        assert 0 <= insight.confidence <= 1
    https = next(i for i in s.insights if i.code == "no_https")
    viewport = next(i for i in s.insights if i.code == "no_viewport")
    assert https.label == "FACT" and viewport.label == "INFERENCE"


def test_prompt_injection_text_is_inert_data() -> None:
    s = analyze_html(BAD_HTML, "http://bad.example.com/")
    # The hostile sentence is just page text: it creates no contacts and no score fields.
    assert s.contacts == []
    assert "IGNORE ALL PREVIOUS INSTRUCTIONS" not in " ".join(i.claim for i in s.insights)


def test_empty_and_malformed_html_do_not_crash() -> None:
    for html in ["", "<<<>>>", "<html><title></title>"]:
        s = analyze_html(html, "https://x.com/")
        assert s.title is None


def test_insight_validation() -> None:
    import pytest

    with pytest.raises(ValueError):
        Insight("c", "e", "u", 1.5, "FACT")
    with pytest.raises(ValueError):
        Insight("c", "e", "u", 0.5, "MAYBE")  # type: ignore[arg-type]
