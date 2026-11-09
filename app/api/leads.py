"""Lead endpoints."""

import uuid
from typing import Annotated, Literal

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.models import Lead
from app.models.lead import LEAD_STATUSES, SERVICES
from app.repositories import company as company_repo
from app.repositories import lead as lead_repo
from app.schemas.lead import LeadCreate, LeadRead, LeadScoreRead

router = APIRouter(prefix="/leads", tags=["leads"])

DB = Annotated[AsyncSession, Depends(get_db)]


def _to_read(lead: Lead) -> LeadRead:
    score = lead_repo.latest_score(lead)
    return LeadRead(
        id=lead.id,
        status=lead.status,
        recommended_service=lead.recommended_service,
        notes=lead.notes,
        company=lead.company,  # type: ignore[arg-type]
        source_name=lead.source.name if lead.source else None,
        latest_score=LeadScoreRead.model_validate(score) if score else None,
        created_at=lead.created_at,
        updated_at=lead.updated_at,
    )


@router.post("", response_model=LeadRead, status_code=status.HTTP_201_CREATED)
async def create_lead(data: LeadCreate, db: DB) -> LeadRead:
    if await company_repo.get(db, data.company_id) is None:
        raise HTTPException(status_code=404, detail="Company not found")
    lead = await lead_repo.create_lead(
        db,
        company_id=data.company_id,
        source_name=data.source_name,
        recommended_service=data.recommended_service,
        notes=data.notes,
    )
    await db.commit()
    return _to_read(lead)


@router.get("", response_model=dict)
async def list_leads(
    db: DB,
    min_score: Annotated[float | None, Query(ge=0, le=100)] = None,
    country: str | None = None,
    service: Annotated[str | None, Query(pattern="^(" + "|".join(SERVICES) + ")$")] = None,
    status_: Annotated[
        str | None, Query(alias="status", pattern="^(" + "|".join(LEAD_STATUSES) + ")$")
    ] = None,
    sort: Literal["score", "created"] = "score",
    limit: Annotated[int, Query(ge=1, le=100)] = 25,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> dict:
    leads, total = await lead_repo.list_leads(
        db,
        min_score=min_score,
        country=country,
        service=service,
        status=status_,
        sort=sort,
        limit=limit,
        offset=offset,
    )
    return {
        "items": [_to_read(lead) for lead in leads],
        "total": total,
        "limit": limit,
        "offset": offset,
    }


@router.get("/{lead_id}", response_model=LeadRead)
async def get_lead(lead_id: uuid.UUID, db: DB) -> LeadRead:
    lead = await lead_repo.get_lead(db, lead_id)
    if lead is None:
        raise HTTPException(status_code=404, detail="Lead not found")
    return _to_read(lead)
