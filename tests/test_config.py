"""Tests for configuration loading."""

from app.core.config import get_settings


def test_settings_load() -> None:
    settings = get_settings()
    assert settings.database_url
    assert settings.log_level
    assert settings.environment
