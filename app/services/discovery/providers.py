"""Concrete discovery providers.

* ManualProvider / CsvProvider - analyst-supplied companies (always available).
* GooglePlacesProvider - Google Places API (New) text search. Requires
  GOOGLE_PLACES_API_KEY. Covered by mocked tests only; it has NOT been
  exercised against the live API yet.
"""

import csv
import io

import httpx

from app.core.config import get_settings
from app.services.discovery.base import (
    DiscoveredCompany,
    LeadSourceProvider,
    ProviderUnavailableError,
)


class ManualProvider(LeadSourceProvider):
    name = "manual"

    def __init__(self, companies: list[DiscoveredCompany]) -> None:
        self._companies = companies

    async def discover(self, query: str | None, limit: int) -> list[DiscoveredCompany]:
        return self._companies[:limit]


class CsvProvider(LeadSourceProvider):
    """CSV with header row; columns: name, website (required), industry, country, location."""

    name = "csv_import"

    def __init__(self, csv_text: str) -> None:
        self._csv_text = csv_text

    async def discover(self, query: str | None, limit: int) -> list[DiscoveredCompany]:
        reader = csv.DictReader(io.StringIO(self._csv_text))
        out: list[DiscoveredCompany] = []
        for row in reader:
            name = (row.get("name") or "").strip()
            website = (row.get("website") or "").strip()
            if not name or not website:
                continue
            out.append(
                DiscoveredCompany(
                    name=name,
                    website=website,
                    industry=(row.get("industry") or "").strip() or None,
                    country=(row.get("country") or "").strip() or None,
                    location=(row.get("location") or "").strip() or None,
                )
            )
            if len(out) >= limit:
                break
        return out


class GooglePlacesProvider(LeadSourceProvider):
    name = "google_places"
    _URL = "https://places.googleapis.com/v1/places:searchText"
    _FIELDS = (
        "places.displayName,places.websiteUri,places.formattedAddress,places.primaryTypeDisplayName"
    )

    def __init__(self, transport: httpx.AsyncBaseTransport | None = None) -> None:
        self._key = get_settings().google_places_api_key
        self._transport = transport

    async def discover(self, query: str | None, limit: int) -> list[DiscoveredCompany]:
        if not self._key:
            raise ProviderUnavailableError("GOOGLE_PLACES_API_KEY is not configured")
        if not query:
            raise ProviderUnavailableError("google_places requires a query")
        async with httpx.AsyncClient(transport=self._transport, timeout=15) as client:
            try:
                response = await client.post(
                    self._URL,
                    headers={"X-Goog-Api-Key": self._key, "X-Goog-FieldMask": self._FIELDS},
                    json={"textQuery": query, "pageSize": min(limit, 20)},
                )
                response.raise_for_status()
            except httpx.HTTPError as exc:
                raise ProviderUnavailableError(
                    f"Places request failed: {exc.__class__.__name__}"
                ) from exc
        out: list[DiscoveredCompany] = []
        for place in response.json().get("places", []):
            website = place.get("websiteUri")
            name = (place.get("displayName") or {}).get("text")
            if not website or not name:
                continue  # no website -> nothing to research
            out.append(
                DiscoveredCompany(
                    name=name,
                    website=website,
                    industry=(place.get("primaryTypeDisplayName") or {}).get("text"),
                    location=place.get("formattedAddress"),
                )
            )
        return out[:limit]
