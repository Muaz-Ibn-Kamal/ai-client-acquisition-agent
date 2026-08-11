"""SQLAlchemy declarative base for all ORM models."""

from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    """Base class for all ORM models.

    No business models are defined in the Foundation stage. Companies,
    contacts, leads, etc. are added in the Lead Discovery step - see
    docs/PHASE_1_SPECIFICATION.md §4.
    """
