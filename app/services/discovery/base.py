"""Provider-based lead discovery (spec §7)."""

from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass(frozen=True)
class DiscoveredCompany:
    name: str
    website: str
    industry: str | None = None
    country: str | None = None
    location: str | None = None
    description: str | None = None


class ProviderUnavailableError(Exception):
    """The provider is not configured (e.g. missing API key) or failed."""


class LeadSourceProvider(ABC):
    #: Stored as LeadSource.name on every lead the provider produces.
    name: str

    @abstractmethod
    async def discover(self, query: str | None, limit: int) -> list[DiscoveredCompany]: ...
