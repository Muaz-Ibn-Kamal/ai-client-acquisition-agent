"""Company data access, including domain-based deduplication."""

import uuid

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Company
from app.schemas.company import CompanyCreate
from app.utils.domain import normalize_domain


async def get_by_domain(session: AsyncSession, domain: str) -> Company | None:
    result = await session.execute(
        select(Company).where(Company.domain == normalize_domain(domain))
    )
    return result.scalar_one_or_none()


async def get_or_create(session: AsyncSession, data: CompanyCreate) -> tuple[Company, bool]:
    """Return (company, created). Existing companies are matched by normalized domain."""
    domain = normalize_domain(data.website)
    existing = await get_by_domain(session, domain)
    if existing is not None:
        return existing, False

    company = Company(
        name=data.name,
        domain=domain,
        website_url=data.website,
        industry=data.industry,
        country=data.country,
        location=data.location,
        description=data.description,
    )
    session.add(company)
    await session.flush()
    return company, True


async def get(session: AsyncSession, company_id: uuid.UUID) -> Company | None:
    return await session.get(Company, company_id)


async def list_companies(
    session: AsyncSession,
    *,
    country: str | None,
    industry: str | None,
    limit: int,
    offset: int,
) -> tuple[list[Company], int]:
    query = select(Company)
    if country:
        query = query.where(func.lower(Company.country) == country.lower())
    if industry:
        query = query.where(func.lower(Company.industry) == industry.lower())
    total = (await session.execute(select(func.count()).select_from(query.subquery()))).scalar_one()
    rows = await session.execute(
        query.order_by(Company.created_at.desc()).limit(limit).offset(offset)
    )
    return list(rows.scalars().all()), total
