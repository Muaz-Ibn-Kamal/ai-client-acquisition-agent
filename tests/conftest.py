"""Shared pytest fixtures.

DB-backed tests run against a throwaway ``<database>_test`` database on the
PostgreSQL server in DATABASE_URL (see docker-compose.yml). Tables are created
from the ORM metadata per test and dropped afterwards; the schema/migration
match is checked separately with ``alembic check``.
"""

from collections.abc import AsyncGenerator

import asyncpg
import pytest
import pytest_asyncio
from fastapi.testclient import TestClient
from httpx import ASGITransport, AsyncClient
from sqlalchemy.engine import make_url
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.pool import NullPool

from app import models as _models  # noqa: F401  (register tables)
from app.core.config import get_settings
from app.db.base import Base
from app.db.session import get_db
from app.main import app


@pytest.fixture
def client() -> TestClient:
    return TestClient(app)


async def _ensure_test_database() -> str:
    url = make_url(get_settings().database_url)
    test_name = f"{url.database}_test"
    conn = await asyncpg.connect(
        user=url.username,
        password=url.password,
        host=url.host,
        port=url.port,
        database="postgres",
    )
    try:
        exists = await conn.fetchval("SELECT 1 FROM pg_database WHERE datname = $1", test_name)
        if not exists:
            await conn.execute(f'CREATE DATABASE "{test_name}"')
    finally:
        await conn.close()
    return url.set(database=test_name).render_as_string(hide_password=False)


@pytest_asyncio.fixture
async def db_engine() -> AsyncGenerator[AsyncEngine, None]:
    test_url = await _ensure_test_database()
    engine = create_async_engine(test_url, poolclass=NullPool)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()


@pytest_asyncio.fixture
async def db_session(db_engine: AsyncEngine) -> AsyncGenerator[AsyncSession, None]:
    async with async_sessionmaker(db_engine, expire_on_commit=False)() as session:
        yield session


@pytest_asyncio.fixture
async def api(db_engine: AsyncEngine) -> AsyncGenerator[AsyncClient, None]:
    factory = async_sessionmaker(db_engine, expire_on_commit=False)

    async def _override() -> AsyncGenerator[AsyncSession, None]:
        async with factory() as session:
            yield session

    app.dependency_overrides[get_db] = _override
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        yield ac
    app.dependency_overrides.clear()
