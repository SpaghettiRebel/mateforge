import asyncio
import os
from pathlib import Path
from typing import AsyncGenerator
from unittest.mock import AsyncMock

import pytest
import pytest_asyncio
from alembic import command
from alembic.config import Config
from httpx import ASGITransport, AsyncClient
from redis.asyncio import Redis
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

os.environ.setdefault("DB_HOST", "localhost")
os.environ.setdefault("DB_PORT", "5432")
os.environ.setdefault("DB_USER", "user")
os.environ.setdefault("DB_PASS", "password")
os.environ.setdefault("DB_NAME", "test_db")
os.environ.setdefault("REDIS_HOST", "localhost")
os.environ.setdefault("REDIS_PORT", "6379")
os.environ.setdefault("JWT_SECRET", "test_secret_key_for_ci_only_change_me_123456")
os.environ.setdefault("MAIL_USERNAME", "test@example.com")
os.environ.setdefault("MAIL_PASSWORD", "password")
os.environ.setdefault("MAIL_FROM", "test@example.com")
os.environ.setdefault("GRPC_SERVICE_TOKEN", "test_grpc_service_token_for_ci_only_123456")
os.environ.setdefault("PUBLIC_APP_URL", "http://testserver")

from auth_service.src.infrastructure.config import settings
from auth_service.src.infrastructure.database import get_async_session
from auth_service.src.infrastructure.models import UserDB
from auth_service.src.infrastructure.redis import get_redis_client
from auth_service.src.main import app

engine = create_async_engine(settings.DATABASE_URL_ASYNCPG, echo=False)


async def _reset_database() -> None:
    if "test" not in settings.DB_NAME.lower():
        raise RuntimeError(f"Refusing to reset non-test database: {settings.DB_NAME}")

    async with engine.begin() as conn:
        await conn.execute(text("DROP SCHEMA IF EXISTS public CASCADE"))
        await conn.execute(text("CREATE SCHEMA public"))

    alembic_cfg = Config(str(Path(__file__).resolve().parents[1] / "alembic.ini"))
    await asyncio.to_thread(command.upgrade, alembic_cfg, "head")


@pytest_asyncio.fixture(scope="session", autouse=True)
async def prepare_database():
    await _reset_database()
    yield
    await engine.dispose()


@pytest_asyncio.fixture
async def db_session() -> AsyncGenerator[AsyncSession, None]:
    connection = await engine.connect()
    transaction = await connection.begin()
    session_factory = async_sessionmaker(bind=connection, class_=AsyncSession, expire_on_commit=False)

    async with session_factory() as session:
        yield session

    if transaction.is_active:
        await transaction.rollback()
    await connection.close()


@pytest_asyncio.fixture(scope="session")
async def redis_client_session() -> AsyncGenerator[Redis, None]:
    client = Redis.from_url(settings.REDIS_URL, decode_responses=True)
    yield client
    await client.aclose()


@pytest_asyncio.fixture
async def redis_client(redis_client_session: Redis) -> AsyncGenerator[Redis, None]:
    await redis_client_session.flushall()
    yield redis_client_session
    await redis_client_session.flushall()


@pytest_asyncio.fixture
async def client(db_session: AsyncSession, redis_client: Redis) -> AsyncGenerator[AsyncClient, None]:
    app.dependency_overrides[get_async_session] = lambda: db_session
    app.dependency_overrides[get_redis_client] = lambda: redis_client

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        yield ac

    app.dependency_overrides.clear()


@pytest.fixture(autouse=True)
def mock_email_client(monkeypatch):
    monkeypatch.setattr("auth_service.src.application.login_service.send_verification_email", AsyncMock())


@pytest_asyncio.fixture
async def verified_user(client: AsyncClient, db_session: AsyncSession):
    payload = {
        "email": "active@test.com",
        "username": "active_user",
        "password": "Strong_password-33",
    }
    await client.post("/auth/register", json=payload)

    user = (await db_session.execute(select(UserDB).where(UserDB.email == payload["email"]))).scalar_one()
    user.is_verified = True
    await db_session.commit()
    await db_session.refresh(user)
    return payload, user
