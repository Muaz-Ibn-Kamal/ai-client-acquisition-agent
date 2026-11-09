"""Discovery, research and scoring endpoints."""

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.repositories import company as company_repo
from app.repositories import lead as lead_repo
from app.schemas.lead import LeadScoreRead
from app.schemas.pipeline import (
    DiscoverRequest,
    DiscoverResponse,
    ResearchResponse,
    ScoreRequest,
)
from app.scrapers.fetcher import SafeFetcher
from app.services.discovery.base import (
    DiscoveredCompany,
    LeadSourceProvider,
    ProviderUnavailableError,
)
from app.services.discovery.providers import CsvProvider, GooglePlacesProvider, ManualProvider
from app.services.discovery.service import run_discovery
from app.services.research import ResearchError, research_company
from app.services.scoring import score_lead_record

router = APIRouter(tags=["pipeline"])

DB = Annotated[AsyncSession, Depends(get_db)]


def get_fetcher() -> SafeFetcher:
    return SafeFetcher()


def _build_provider(req: DiscoverRequest) -> LeadSourceProvider:
    if req.provider == "manual":
        if not req.companies:
            raise HTTPException(422, "provider 'manual' needs a non-empty 'companies' list")
        return ManualProvider([DiscoveredCompany(**c.model_dump()) for c in req.companies])
    if req.provider == "csv":
        if not req.csv_text:
            raise HTTPException(422, "provider 'csv' needs 'csv_text'")
        return CsvProvider(req.csv_text)
    return GooglePlacesProvider()


@router.post("/discover", response_model=DiscoverResponse)
async def discover(req: DiscoverRequest, db: DB) -> DiscoverResponse:
    provider = _build_provider(req)
    try:
        result = await run_discovery(db, provider, req.query, req.limit)
    except ProviderUnavailableError as exc:
        raise HTTPException(503, str(exc)) from exc
    await db.commit()
    return DiscoverResponse(
        provider=result.provider,
        found=result.found,
        new_companies=result.new_companies,
        duplicates=result.duplicates,
        invalid=result.invalid,
        lead_ids=[str(i) for i in result.lead_ids],
    )


@router.post("/research/{company_id}", response_model=ResearchResponse)
async def research(
    company_id: uuid.UUID, db: DB, fetcher: Annotated[SafeFetcher, Depends(get_fetcher)]
) -> ResearchResponse:
    company = await company_repo.get(db, company_id)
    if company is None:
        raise HTTPException(404, "Company not found")
    try:
        result = await research_company(db, company, fetcher)
    except ResearchError as exc:
        raise HTTPException(502, f"Research failed: {exc}") from exc
    await db.commit()
    data = result.signals.to_json()
    return ResearchResponse(
        company_id=str(company.id),
        url=result.analysis.url,
        title=result.analysis.title,
        technologies=result.signals.technologies,
        contacts_added=result.contacts_added,
        opportunities_added=result.opportunities_added,
        insights=data["insights"],  # type: ignore[arg-type]
    )


@router.post("/score/{lead_id}", response_model=LeadScoreRead)
async def score(lead_id: uuid.UUID, db: DB, body: ScoreRequest | None = None) -> LeadScoreRead:
    lead = await lead_repo.get_lead(db, lead_id)
    if lead is None:
        raise HTTPException(404, "Lead not found")
    try:
        overrides = (body or ScoreRequest()).to_signals()
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from exc
    saved = await score_lead_record(db, lead, overrides)
    await db.commit()
    return LeadScoreRead.model_validate(saved)
