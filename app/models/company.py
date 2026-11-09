"""Company and Contact models (spec §4, §4.1)."""

import uuid
from datetime import datetime

import sqlalchemy as sa
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.mixins import TimestampMixin, UUIDPrimaryKeyMixin, _utcnow

CONTACT_TYPES = ("business_inbox", "named_individual")


class Company(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "companies"

    name: Mapped[str] = mapped_column(sa.String(255))
    # Normalized domain (see app.utils.domain). Unique -> company deduplication.
    domain: Mapped[str] = mapped_column(sa.String(255), unique=True, index=True)
    website_url: Mapped[str | None] = mapped_column(sa.String(2048))
    industry: Mapped[str | None] = mapped_column(sa.String(255), index=True)
    country: Mapped[str | None] = mapped_column(sa.String(100), index=True)
    location: Mapped[str | None] = mapped_column(sa.String(255))
    description: Mapped[str | None] = mapped_column(sa.Text)

    contacts: Mapped[list["Contact"]] = relationship(
        back_populates="company", cascade="all, delete-orphan"
    )


class Contact(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """Public business contact information with provenance (spec §4.1).

    Only publicly available business contact details belong here. Suppression
    fields are schema support only; no outreach logic exists in Phase 1.
    """

    __tablename__ = "contacts"
    __table_args__ = (
        sa.CheckConstraint(
            "contact_type IN ('business_inbox', 'named_individual')", name="ck_contacts_type"
        ),
    )

    company_id: Mapped[uuid.UUID] = mapped_column(
        sa.ForeignKey("companies.id", ondelete="CASCADE"), index=True
    )
    name: Mapped[str | None] = mapped_column(sa.String(255))
    position: Mapped[str | None] = mapped_column(sa.String(255))
    email: Mapped[str | None] = mapped_column(sa.String(320))
    phone: Mapped[str | None] = mapped_column(sa.String(50))
    linkedin_url: Mapped[str | None] = mapped_column(sa.String(2048))

    contact_type: Mapped[str] = mapped_column(sa.String(30))
    is_public_business_contact: Mapped[bool] = mapped_column(sa.Boolean, default=True)
    source_attribution: Mapped[str] = mapped_column(sa.String(2048))
    data_provenance: Mapped[str] = mapped_column(sa.String(255))
    collected_at: Mapped[datetime] = mapped_column(sa.DateTime(timezone=True), default=_utcnow)

    is_suppressed: Mapped[bool] = mapped_column(sa.Boolean, default=False, server_default="false")
    suppressed_at: Mapped[datetime | None] = mapped_column(sa.DateTime(timezone=True))
    suppression_reason: Mapped[str | None] = mapped_column(sa.String(255))
    retention_notes: Mapped[str | None] = mapped_column(sa.Text)

    company: Mapped[Company] = relationship(back_populates="contacts")
