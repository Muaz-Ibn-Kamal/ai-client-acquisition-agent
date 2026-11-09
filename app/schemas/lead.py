import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from app.models.lead import LEAD_STATUSES, SERVICES
from app.schemas.company import CompanyRead

LeadStatus = Literal[LEAD_STATUSES]  # type: ignore[valid-type]
Service = Literal[SERVICES]  # type: ignore[valid-type]


class LeadCreate(BaseModel):
    company_id: uuid.UUID
    source_name: str | None = Field(default=None, max_length=100)
    recommended_service: Service | None = None
    notes: str | None = None


class LeadScoreRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    total_score: float
    service_fit: float
    opportunity_strength: float
    business_quality: float
    need_signal: float
    project_value_potential: float
    contactability: float
    confidence: float
    reasons: dict
    created_at: datetime


class LeadRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    status: str
    recommended_service: str | None
    notes: str | None
    company: CompanyRead
    source_name: str | None = None
    latest_score: LeadScoreRead | None = None
    created_at: datetime
    updated_at: datetime
