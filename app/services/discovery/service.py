"""Run a provider, dedupe companies by domain, and create leads."""

from dataclasses import dataclass, field

from sqlalchemy.ext.asyncio import AsyncSession

from app.repositories import company as company_repo
from app.repositories import lead as lead_repo
from app.schemas.company import CompanyCreate
from app.services.discovery.base import LeadSourceProvider


@dataclass
class DiscoveryResult:
    provider: str
    found: int = 0
    new_companies: int = 0
    duplicates: int = 0
    invalid: int = 0
    lead_ids: list = field(default_factory=list)


async def run_discovery(
    session: AsyncSession, provider: LeadSourceProvider, query: str | None, limit: int
) -> DiscoveryResult:
    result = DiscoveryResult(provider=provider.name)
    discovered = await provider.discover(query, limit)
    result.found = len(discovered)
    for item in discovered:
        try:
            data = CompanyCreate(
                name=item.name,
                website=item.website,
                industry=item.industry,
                country=item.country,
                location=item.location,
                description=item.description,
            )
        except ValueError:
            result.invalid += 1
            continue
        company, created = await company_repo.get_or_create(session, data)
        if not created:
            result.duplicates += 1
            continue
        result.new_companies += 1
        lead = await lead_repo.create_lead(
            session,
            company_id=company.id,
            source_name=provider.name,
            recommended_service=None,
            notes=None,
        )
        result.lead_ids.append(lead.id)
    return result
