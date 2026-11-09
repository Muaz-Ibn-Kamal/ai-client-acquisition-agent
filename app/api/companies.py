"""Company endpoints."""

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.repositories import company as company_repo
from app.schemas.company import CompanyCreate, CompanyRead

router = APIRouter(prefix="/companies", tags=["companies"])

DB = Annotated[AsyncSession, Depends(get_db)]


@router.post("", response_model=CompanyRead, status_code=status.HTTP_201_CREATED)
async def create_company(data: CompanyCreate, response: Response, db: DB) -> CompanyRead:
    """Create a company; an existing normalized domain is returned (200), not duplicated."""
    company, created = await company_repo.get_or_create(db, data)
    await db.commit()
    if not created:
        response.status_code = status.HTTP_200_OK
    return CompanyRead.model_validate(company)


@router.get("", response_model=dict)
async def list_companies(
    db: DB,
    country: str | None = None,
    industry: str | None = None,
    limit: Annotated[int, Query(ge=1, le=100)] = 25,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> dict:
    items, total = await company_repo.list_companies(
        db, country=country, industry=industry, limit=limit, offset=offset
    )
    return {
        "items": [CompanyRead.model_validate(c) for c in items],
        "total": total,
        "limit": limit,
        "offset": offset,
    }


@router.get("/{company_id}", response_model=CompanyRead)
async def get_company(company_id: uuid.UUID, db: DB) -> CompanyRead:
    company = await company_repo.get(db, company_id)
    if company is None:
        raise HTTPException(status_code=404, detail="Company not found")
    return CompanyRead.model_validate(company)
