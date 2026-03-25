import os
from typing import AsyncGenerator
from unittest.mock import AsyncMock

import pytest
from httpx import ASGITransport, AsyncClient
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from auth_service.src.infrastructure.database import Base, get_async_session
from auth_service.src.infrastructure.redis import get_redis_client
from auth_service.src.main import app

DATABASE_URL = os.getenv("DATABASE_URL")
REDIS_URL = os.getenv("REDIS_URL")

engine = create_async_engine(DATABASE_URL, echo=False)


@pytest.fixture(scope="session", autouse=True)
async def prepare_database():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


@pytest.fixture
async def db_session() -> AsyncGenerator[AsyncSession, None]:
    connection = await engine.connect()
    transaction = await connection.begin()

    SessionLocal = async_sessionmaker(
        bind=connection,
        class_=AsyncSession,
        expire_on_commit=False
    )

    async with SessionLocal() as session:
        yield session

    await transaction.rollback()
    await connection.close()


@pytest.fixture(scope="session")
async def redis_client_session():
    client = Redis.from_url(REDIS_URL, decode_responses=True)
    yield client
    await client.aclose()


@pytest.fixture
async def redis_client(redis_client_session):
    yield redis_client_session
    await redis_client_session.flushall()


@pytest.fixture
async def client(db_session, redis_client) -> AsyncGenerator[AsyncClient, None]:
    app.dependency_overrides[get_async_session] = lambda: db_session
    app.dependency_overrides[get_redis_client] = lambda: redis_client

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test"
    ) as ac:
        yield ac

    app.dependency_overrides.clear()


@pytest.fixture(autouse=True)
def mock_email_client(monkeypatch):
    monkeypatch.setattr("fastapi_mail.FastMail.send_message", AsyncMock())


@pytest.fixture(autouse=True)
async def clear_data(db_session, redis_client):
    yield
    from sqlalchemy import delete

    from auth_service.src.infrastructure.models import UserDB

    await db_session.execute(delete(UserDB))
    await db_session.commit()
    await redis_client.flushall()


@pytest.fixture
async def verified_user(client, db_session):
    payload = {
        "email": "active@test.com",
        "username": "active_user",
        "password": "Strong_password-33"
    }

    await client.post("/auth/register", json={**payload, "fingerprint": "test_fp"})

    from sqlalchemy import select

    from auth_service.src.infrastructure.models import UserDB

    stmt = select(UserDB).where(UserDB.email == payload["email"])
    user = (await db_session.execute(stmt)).scalar_one()

    user.is_verified = True
    await db_session.commit()

    return payload, user.id
