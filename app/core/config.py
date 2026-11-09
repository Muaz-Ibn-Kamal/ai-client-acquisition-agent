"""Application configuration, loaded from environment variables.

Only settings genuinely needed by the Foundation stage are defined here.
Do not add settings for features that don't exist yet (see
docs/PHASE_1_SPECIFICATION.md - Step 4 discipline: no invented credentials).
"""

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Environment-driven application settings.

    Values are read from environment variables, or a local .env file during
    development (see .env.example). Never hard-code secrets here.
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_name: str = "AI Client Acquisition Agent"
    environment: str = "development"
    log_level: str = "INFO"
    database_url: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/client_acquisition"

    # Outbound fetching (website research). See docs/PHASE_1_SPECIFICATION.md §10.
    fetch_timeout_seconds: float = 10.0
    fetch_max_bytes: int = 1_000_000
    fetch_max_redirects: int = 3
    fetch_user_agent: str = (
        "ClientAcquisitionResearchBot/0.1 (+business research; respects robots.txt)"
    )

    # Optional discovery provider credentials. Providers are disabled when unset.
    google_places_api_key: str | None = None


@lru_cache
def get_settings() -> Settings:
    """Cached settings accessor so the environment isn't re-parsed on every call."""
    return Settings()
