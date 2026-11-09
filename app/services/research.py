"""Company website research: fetch, analyze, persist evidence and public contacts."""

from dataclasses import dataclass
from datetime import UTC, datetime

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Company, Contact, Lead, Opportunity, WebsiteAnalysis
from app.scrapers.analyzer import WebsiteSignals, analyze_html
from app.scrapers.fetcher import FetchError, SafeFetcher

# Insight codes that describe a problem we could help with -> recommended service.
_OPPORTUNITY_SERVICES = {
    "no_https": "web_development",
    "no_viewport": "website_redesign",
    "no_cta": "website_redesign",
    "no_meta_description": "web_development",
    "no_title": "web_development",
    "images_missing_alt": "web_development",
}


class ResearchError(Exception):
    pass


@dataclass
class ResearchResult:
    analysis: WebsiteAnalysis
    contacts_added: int
    opportunities_added: int
    signals: WebsiteSignals


async def research_company(
    session: AsyncSession, company: Company, fetcher: SafeFetcher | None = None
) -> ResearchResult:
    fetcher = fetcher or SafeFetcher()
    url = company.website_url or f"https://{company.domain}"
    if "://" not in url:
        url = f"https://{url}"
    try:
        page = await fetcher.fetch_page(url)
    except FetchError as exc:
        raise ResearchError(str(exc)) from exc
    if page.status_code >= 400:
        raise ResearchError(f"website returned HTTP {page.status_code}")

    signals = analyze_html(page.html, page.url)
    analysis = WebsiteAnalysis(
        company_id=company.id,
        url=page.url,
        title=signals.title,
        meta_description=signals.meta_description,
        signals=signals.to_json(),
    )
    session.add(analysis)

    existing = await session.execute(select(Contact).where(Contact.company_id == company.id))
    known = {(c.email, c.phone) for c in existing.scalars()}
    added = 0
    for found in signals.contacts:
        # Only keep emails on the company's own domain (avoid private/personal addresses).
        if found.email and not found.email.endswith(("@" + company.domain, "." + company.domain)):
            continue
        if (found.email, found.phone) in known:
            continue
        known.add((found.email, found.phone))
        session.add(
            Contact(
                company_id=company.id,
                email=found.email,
                phone=found.phone,
                contact_type=found.contact_type,
                is_public_business_contact=True,
                source_attribution=found.source_url,
                data_provenance="published on company website (mailto/tel link or visible text)",
                collected_at=datetime.now(UTC),
                retention_notes="Review before any future outreach; honour opt-outs.",
            )
        )
        added += 1

    leads = (
        (await session.execute(select(Lead).where(Lead.company_id == company.id))).scalars().all()
    )
    opportunities = 0
    for lead in leads:
        await session.execute(delete(Opportunity).where(Opportunity.lead_id == lead.id))
        for insight in signals.insights:
            service = _OPPORTUNITY_SERVICES.get(insight.code)
            if service is None:
                continue
            session.add(
                Opportunity(
                    lead_id=lead.id,
                    service=service,
                    claim=insight.claim,
                    evidence=insight.evidence,
                    source_url=insight.source_url,
                    observed_at=insight.observed_at,
                    confidence=insight.confidence,
                    label=insight.label,
                )
            )
            opportunities += 1
        if lead.status == "new":
            lead.status = "researched"
    await session.flush()
    return ResearchResult(analysis, added, opportunities, signals)
