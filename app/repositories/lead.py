"""Lead data access: creation, filtering and ranking by latest score."""

import uuid
from typing import Literal

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models import Company, Lead, LeadScore, LeadSource
from app.scoring import ScoreResult, ScoringWeights


async def _get_or_create_source(session: AsyncSession, name: str) -> LeadSource:
    result = await session.execute(select(LeadSource).where(LeadSource.name == name))
    source = result.scalar_one_or_none()
    if source is None:
        source = LeadSource(name=name)
        session.add(source)
        await session.flush()
    return source


async def create_lead(
    session: AsyncSession,
    *,
    company_id: uuid.UUID,
    source_name: str | None,
    recommended_service: str | None,
    notes: str | None,
) -> Lead:
    source = await _get_or_create_source(session, source_name) if source_name else None
    lead = Lead(
        company_id=company_id,
        lead_source_id=source.id if source else None,
        recommended_service=recommended_service,
        notes=notes,
    )
    session.add(lead)
    await session.flush()
    await session.refresh(lead, ["company", "source", "scores"])
    return lead


def latest_score(lead: Lead) -> LeadScore | None:
    return lead.scores[-1] if lead.scores else None


async def get_lead(session: AsyncSession, lead_id: uuid.UUID) -> Lead | None:
    result = await session.execute(
        select(Lead).where(Lead.id == lead_id).options(selectinload(Lead.scores))
    )
    return result.scalar_one_or_none()


async def list_leads(
    session: AsyncSession,
    *,
    min_score: float | None,
    country: str | None,
    service: str | None,
    status: str | None,
    sort: Literal["score", "created"],
    limit: int,
    offset: int,
) -> tuple[list[Lead], int]:
    # Newest score per lead (scores are append-only).
    ranked = select(
        LeadScore.lead_id,
        LeadScore.total_score,
        func.row_number()
        .over(partition_by=LeadScore.lead_id, order_by=LeadScore.created_at.desc())
        .label("rn"),
    ).subquery()
    newest = select(ranked.c.lead_id, ranked.c.total_score).where(ranked.c.rn == 1).subquery()

    query = (
        select(Lead)
        .join(Company, Lead.company_id == Company.id)
        .outerjoin(newest, newest.c.lead_id == Lead.id)
    )
    if min_score is not None:
        query = query.where(newest.c.total_score >= min_score)
    if country:
        query = query.where(func.lower(Company.country) == country.lower())
    if service:
        query = query.where(Lead.recommended_service == service)
    if status:
        query = query.where(Lead.status == status)

    total = (await session.execute(select(func.count()).select_from(query.subquery()))).scalar_one()
    if sort == "score":
        query = query.order_by(newest.c.total_score.desc().nulls_last(), Lead.created_at.desc())
    else:
        query = query.order_by(Lead.created_at.desc())
    rows = await session.execute(
        query.options(selectinload(Lead.scores)).limit(limit).offset(offset)
    )
    return list(rows.scalars().unique().all()), total


async def save_score(
    session: AsyncSession,
    lead: Lead,
    result: ScoreResult,
    weights: ScoringWeights,
) -> LeadScore:
    """Persist a scoring run (append-only)."""
    c = result.component_scores()
    score = LeadScore(
        lead_id=lead.id,
        total_score=result.total_score,
        confidence=result.confidence,
        reasons=result.reasons(),
        weights=weights.as_dict(),
        **c,
    )
    session.add(score)
    await session.flush()
    return score
