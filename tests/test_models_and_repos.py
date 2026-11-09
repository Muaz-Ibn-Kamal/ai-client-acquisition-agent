import pytest
from sqlalchemy.exc import IntegrityError

from app.models import Company, Contact, Lead, Opportunity
from app.repositories import company as company_repo
from app.repositories import lead as lead_repo
from app.schemas.company import CompanyCreate
from app.scoring import COMPONENT_FACTORS, FactorSignal, ScoringWeights, score_lead


async def test_company_dedup_by_normalized_domain(db_session) -> None:
    a, created_a = await company_repo.get_or_create(
        db_session, CompanyCreate(name="Acme", website="https://www.Acme.com/")
    )
    b, created_b = await company_repo.get_or_create(
        db_session, CompanyCreate(name="Acme Inc", website="http://acme.com/about")
    )
    assert created_a is True and created_b is False
    assert a.id == b.id and a.domain == "acme.com"


async def test_duplicate_domain_blocked_by_db(db_session) -> None:
    db_session.add_all([Company(name="A", domain="x.com"), Company(name="B", domain="x.com")])
    with pytest.raises(IntegrityError):
        await db_session.flush()


async def test_ids_and_timestamps_set(db_session) -> None:
    company, _ = await company_repo.get_or_create(
        db_session, CompanyCreate(name="Acme", website="acme.com")
    )
    assert company.id is not None
    assert company.created_at is not None and company.updated_at is not None


async def test_contact_requires_provenance_and_valid_type(db_session) -> None:
    company, _ = await company_repo.get_or_create(
        db_session, CompanyCreate(name="Acme", website="acme.com")
    )
    db_session.add(
        Contact(
            company_id=company.id,
            email="hello@acme.com",
            contact_type="business_inbox",
            source_attribution="https://acme.com/contact",
            data_provenance="public website",
        )
    )
    await db_session.flush()
    contact = (await db_session.execute(__import__("sqlalchemy").select(Contact))).scalar_one()
    assert contact.is_public_business_contact is True
    assert contact.is_suppressed is False
    assert contact.collected_at is not None

    db_session.add(
        Contact(
            company_id=company.id, contact_type="bogus", source_attribution="x", data_provenance="x"
        )
    )
    with pytest.raises(IntegrityError):
        await db_session.flush()


async def test_opportunity_label_and_confidence_constraints(db_session) -> None:
    company, _ = await company_repo.get_or_create(
        db_session, CompanyCreate(name="Acme", website="acme.com")
    )
    lead = await lead_repo.create_lead(
        db_session, company_id=company.id, source_name=None, recommended_service=None, notes=None
    )
    db_session.add(
        Opportunity(
            lead_id=lead.id,
            claim="Weak CTA",
            evidence="No primary CTA on homepage",
            source_url="https://acme.com/",
            confidence=0.82,
            label="INFERENCE",
        )
    )
    await db_session.flush()
    db_session.add(
        Opportunity(
            lead_id=lead.id, claim="c", evidence="e", source_url="u", confidence=1.4, label="FACT"
        )
    )
    with pytest.raises(IntegrityError):
        await db_session.flush()


async def test_lead_creation_and_score_persistence(db_session) -> None:
    company, _ = await company_repo.get_or_create(
        db_session, CompanyCreate(name="Acme", website="acme.com", country="USA")
    )
    lead = await lead_repo.create_lead(
        db_session,
        company_id=company.id,
        source_name="manual",
        recommended_service="website_redesign",
        notes=None,
    )
    assert lead.source is not None
    assert lead.status == "new" and lead.source.name == "manual"

    signals = {c: {f: FactorSignal(0.5) for f in fs} for c, fs in COMPONENT_FACTORS.items()}
    result = score_lead(signals)
    saved = await lead_repo.save_score(db_session, lead, result, ScoringWeights())
    assert saved.total_score == 50
    assert saved.weights["service_fit"] == 25
    assert saved.reasons["service_fit"]
    assert isinstance(lead, Lead)
