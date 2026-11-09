"""Lead, LeadSource, Opportunity, WebsiteAnalysis and LeadScore models."""

import uuid
from datetime import datetime
from typing import Any

import sqlalchemy as sa
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.company import Company
from app.models.mixins import TimestampMixin, UUIDPrimaryKeyMixin, _utcnow

LEAD_STATUSES = (
    "new",
    "researched",
    "audited",
    "qualified",
    "rejected",
)
SERVICES = (
    "web_development",
    "website_redesign",
    "ecommerce",
    "landing_page",
    "ui_ux_design",
    "graphic_design",
    "branding",
    "maintenance",
    "white_label",
)
INSIGHT_LABELS = ("FACT", "INFERENCE", "UNKNOWN")


class LeadSource(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """Where a lead came from (provider name, directory, manual entry...)."""

    __tablename__ = "lead_sources"

    name: Mapped[str] = mapped_column(sa.String(100), unique=True)
    source_type: Mapped[str] = mapped_column(sa.String(50), default="manual")
    description: Mapped[str | None] = mapped_column(sa.Text)


class Lead(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "leads"

    company_id: Mapped[uuid.UUID] = mapped_column(
        sa.ForeignKey("companies.id", ondelete="CASCADE"), index=True
    )
    lead_source_id: Mapped[uuid.UUID | None] = mapped_column(
        sa.ForeignKey("lead_sources.id", ondelete="SET NULL")
    )
    status: Mapped[str] = mapped_column(sa.String(30), default="new", index=True)
    recommended_service: Mapped[str | None] = mapped_column(sa.String(50), index=True)
    notes: Mapped[str | None] = mapped_column(sa.Text)

    company: Mapped[Company] = relationship(lazy="joined")
    source: Mapped[LeadSource | None] = relationship(lazy="joined")
    opportunities: Mapped[list["Opportunity"]] = relationship(
        back_populates="lead", cascade="all, delete-orphan"
    )
    scores: Mapped[list["LeadScore"]] = relationship(
        back_populates="lead", cascade="all, delete-orphan", order_by="LeadScore.created_at"
    )


class Opportunity(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """An evidence-backed project opportunity (spec §8 evidence-first format)."""

    __tablename__ = "opportunities"
    __table_args__ = (
        sa.CheckConstraint("label IN ('FACT', 'INFERENCE', 'UNKNOWN')", name="ck_opp_label"),
        sa.CheckConstraint("confidence >= 0 AND confidence <= 1", name="ck_opp_confidence"),
    )

    lead_id: Mapped[uuid.UUID] = mapped_column(
        sa.ForeignKey("leads.id", ondelete="CASCADE"), index=True
    )
    service: Mapped[str | None] = mapped_column(sa.String(50))
    claim: Mapped[str] = mapped_column(sa.Text)
    evidence: Mapped[str] = mapped_column(sa.Text)
    source_url: Mapped[str] = mapped_column(sa.String(2048))
    observed_at: Mapped[datetime] = mapped_column(sa.DateTime(timezone=True), default=_utcnow)
    confidence: Mapped[float] = mapped_column(sa.Float)
    label: Mapped[str] = mapped_column(sa.String(10))

    lead: Mapped[Lead] = relationship(back_populates="opportunities")


class WebsiteAnalysis(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """Raw public-website signals for a company (populated by the research step)."""

    __tablename__ = "website_analysis"

    company_id: Mapped[uuid.UUID] = mapped_column(
        sa.ForeignKey("companies.id", ondelete="CASCADE"), index=True
    )
    url: Mapped[str] = mapped_column(sa.String(2048))
    fetched_at: Mapped[datetime] = mapped_column(sa.DateTime(timezone=True), default=_utcnow)
    title: Mapped[str | None] = mapped_column(sa.String(1000))
    meta_description: Mapped[str | None] = mapped_column(sa.Text)
    signals: Mapped[dict[str, Any]] = mapped_column(sa.JSON, default=dict)


class LeadScore(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """One scoring run. Scores are append-only so history is preserved."""

    __tablename__ = "lead_scores"
    __table_args__ = (
        sa.CheckConstraint("total_score >= 0 AND total_score <= 100", name="ck_score_total"),
        sa.CheckConstraint("confidence >= 0 AND confidence <= 1", name="ck_score_confidence"),
    )

    lead_id: Mapped[uuid.UUID] = mapped_column(
        sa.ForeignKey("leads.id", ondelete="CASCADE"), index=True
    )
    total_score: Mapped[float] = mapped_column(sa.Float, index=True)
    service_fit: Mapped[float] = mapped_column(sa.Float)
    opportunity_strength: Mapped[float] = mapped_column(sa.Float)
    business_quality: Mapped[float] = mapped_column(sa.Float)
    need_signal: Mapped[float] = mapped_column(sa.Float)
    project_value_potential: Mapped[float] = mapped_column(sa.Float)
    contactability: Mapped[float] = mapped_column(sa.Float)
    confidence: Mapped[float] = mapped_column(sa.Float)
    # Per-component reasons and the weights used, so a score can be audited later.
    reasons: Mapped[dict[str, Any]] = mapped_column(sa.JSON, default=dict)
    weights: Mapped[dict[str, Any]] = mapped_column(sa.JSON, default=dict)

    lead: Mapped[Lead] = relationship(back_populates="scores")
