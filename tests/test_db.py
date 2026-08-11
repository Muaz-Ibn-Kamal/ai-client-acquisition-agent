"""Tests for database configuration and connectivity.

test_database_connectivity requires a reachable PostgreSQL instance (see
docker-compose.yml / README "PostgreSQL" section for local setup).
"""

import pytest
from sqlalchemy import text

from app.db.session import get_engine


def test_engine_initializes() -> None:
    engine = get_engine()
    assert engine is not None


@pytest.mark.asyncio
async def test_database_connectivity() -> None:
    engine = get_engine()
    async with engine.connect() as conn:
        result = await conn.execute(text("SELECT 1"))
        assert result.scalar() == 1
