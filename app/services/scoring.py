"""Score a lead from research data plus optional analyst overrides."""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Contact, Lead, LeadScore, WebsiteAnalysis
from app.repositories import lead as lead_repo
from app.scoring import ScoringSignals, ScoringWeights, score_lead
from app.scoring.signals import derive_signals, merge_overrides


async def score_lead_record(
    session: AsyncSession,
    lead: Lead,
    overrides: ScoringSignals | None = None,
    weights: ScoringWeights | None = None,
) -> LeadScore:
    weights = weights or ScoringWeights()
    analysis = (
        await session.execute(
            select(WebsiteAnalysis)
            .where(WebsiteAnalysis.company_id == lead.company_id)
            .order_by(WebsiteAnalysis.fetched_at.desc())
            .limit(1)
        )
    ).scalar_one_or_none()
    contacts = list(
        (await session.execute(select(Contact).where(Contact.company_id == lead.company_id)))
        .scalars()
        .all()
    )
    signals = merge_overrides(derive_signals(analysis, contacts), overrides or {})
    result = score_lead(signals, weights)
    return await lead_repo.save_score(session, lead, result, weights)
