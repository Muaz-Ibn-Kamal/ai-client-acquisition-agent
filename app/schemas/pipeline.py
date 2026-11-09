from typing import Literal

from pydantic import BaseModel, Field

from app.scoring import COMPONENT_FACTORS, FactorSignal, ScoringSignals


class DiscoveredCompanyIn(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    website: str
    industry: str | None = None
    country: str | None = None
    location: str | None = None


class DiscoverRequest(BaseModel):
    provider: Literal["manual", "csv", "google_places"]
    query: str | None = Field(default=None, max_length=300)
    limit: int = Field(default=20, ge=1, le=100)
    companies: list[DiscoveredCompanyIn] = Field(default_factory=list, max_length=100)
    csv_text: str | None = Field(default=None, max_length=500_000)


class DiscoverResponse(BaseModel):
    provider: str
    found: int
    new_companies: int
    duplicates: int
    invalid: int
    lead_ids: list[str]


class ResearchResponse(BaseModel):
    company_id: str
    url: str
    title: str | None
    technologies: list[str]
    contacts_added: int
    opportunities_added: int
    insights: list[dict]


class FactorOverride(BaseModel):
    value: float | None = Field(ge=0, le=1)
    reason: str = Field(default="", max_length=300)


class ScoreRequest(BaseModel):
    """Optional analyst-supplied signals (component -> factor -> value)."""

    overrides: dict[str, dict[str, FactorOverride]] = Field(default_factory=dict)

    def to_signals(self) -> ScoringSignals:
        out: ScoringSignals = {}
        for component, factors in self.overrides.items():
            if component not in COMPONENT_FACTORS:
                raise ValueError(f"unknown component {component!r}")
            for factor, o in factors.items():
                if factor not in COMPONENT_FACTORS[component]:
                    raise ValueError(f"unknown factor {factor!r} for {component}")
                out.setdefault(component, {})[factor] = FactorSignal(o.value, o.reason)
        return out
