import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.utils.domain import normalize_domain


class CompanyCreate(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    website: str = Field(description="Company website URL or bare domain")
    industry: str | None = Field(default=None, max_length=255)
    country: str | None = Field(default=None, max_length=100)
    location: str | None = Field(default=None, max_length=255)
    description: str | None = None

    @field_validator("website")
    @classmethod
    def _validate_website(cls, value: str) -> str:
        normalize_domain(value)  # raises ValueError -> 422
        return value.strip()


class CompanyRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    domain: str
    website_url: str | None
    industry: str | None
    country: str | None
    location: str | None
    description: str | None
    created_at: datetime
    updated_at: datetime
