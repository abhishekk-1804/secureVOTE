"""
Shared test fixtures for SecureVOTE backend tests.

Uses SQLite in-memory for fast isolated tests.
"""

import asyncio
from typing import AsyncGenerator

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.database import Base, get_db
from app.main import app
from app.models import User
from app.utils.security import hash_password


# In-memory SQLite for test isolation
TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"



@pytest_asyncio.fixture
async def db_engine():
    """Create a fresh in-memory database for each test."""
    engine = create_async_engine(TEST_DATABASE_URL, echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()


@pytest_asyncio.fixture
async def db_session(db_engine) -> AsyncGenerator[AsyncSession, None]:
    """Provide a transactional database session for tests."""
    session_factory = async_sessionmaker(
        db_engine, class_=AsyncSession, expire_on_commit=False
    )
    async with session_factory() as session:
        yield session


@pytest_asyncio.fixture
async def client(db_engine) -> AsyncGenerator[AsyncClient, None]:
    """
    Create an HTTPX async test client with overridden DB dependency.

    Each test gets a fresh in-memory database.
    """
    session_factory = async_sessionmaker(
        db_engine, class_=AsyncSession, expire_on_commit=False
    )

    async def override_get_db():
        async with session_factory() as session:
            try:
                yield session
                await session.commit()
            except Exception:
                await session.rollback()
                raise

    app.dependency_overrides[get_db] = override_get_db

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac

    app.dependency_overrides.clear()


@pytest_asyncio.fixture
async def admin_token(client: AsyncClient) -> str:
    """Register an admin user and return their JWT token."""
    await client.post(
        "/api/auth/register",
        json={"username": "admin", "password": "admin123", "role": "ADMIN"},
    )
    resp = await client.post(
        "/api/auth/login",
        json={"username": "admin", "password": "admin123"},
    )
    return resp.json()["access_token"]


@pytest_asyncio.fixture
async def admin_headers(admin_token: str) -> dict[str, str]:
    """Return auth headers for admin user."""
    return {"Authorization": f"Bearer {admin_token}"}


@pytest_asyncio.fixture
async def auditor_token(client: AsyncClient) -> str:
    """Register an auditor user and return their JWT token."""
    await client.post(
        "/api/auth/register",
        json={"username": "auditor", "password": "audit123", "role": "AUDITOR"},
    )
    resp = await client.post(
        "/api/auth/login",
        json={"username": "auditor", "password": "audit123"},
    )
    return resp.json()["access_token"]


@pytest_asyncio.fixture
async def observer_token(client: AsyncClient) -> str:
    """Register an observer user and return their JWT token."""
    await client.post(
        "/api/auth/register",
        json={"username": "observer", "password": "obs12345", "role": "OBSERVER"},
    )
    resp = await client.post(
        "/api/auth/login",
        json={"username": "observer", "password": "obs12345"},
    )
    return resp.json()["access_token"]
