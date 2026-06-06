import asyncio
import os
from pathlib import Path
from typing import AsyncGenerator
from uuid import UUID, uuid4

import pytest
import pytest_asyncio
from alembic import command
from alembic.config import Config
from httpx import ASGITransport, AsyncClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

os.environ.setdefault("DB_HOST", "localhost")
os.environ.setdefault("DB_PORT", "5433")
os.environ.setdefault("DB_USER", "user")
os.environ.setdefault("DB_PASS", "password")
os.environ.setdefault("DB_NAME", "test_db")
os.environ.setdefault("REDIS_HOST", "localhost")
os.environ.setdefault("REDIS_PORT", "6380")
os.environ.setdefault("JWT_SECRET", "test_secret_key_for_ci_only_change_me_123456")
os.environ.setdefault("USERS_SERVICE_URL", "http://localhost:8000")
os.environ.setdefault("GRPC_SERVICE_TOKEN", "test_grpc_service_token_for_ci_only_123456")

from projects_service.src.infrastructure.config import settings
from projects_service.src.infrastructure.database import get_async_session
from projects_service.src.main import app
from projects_service.src.presentation.dependencies import (
    get_current_user_id,
    get_optional_user_id,
    get_users_gateway,
)

engine = create_async_engine(settings.DATABASE_URL_ASYNCPG, echo=False, poolclass=NullPool)


class FakeUsersGateway:
    def __init__(self):
        self.existing_users: set[UUID] = set()
        self.unavailable = False
        self.calls: list[UUID] = []

    async def check_user_exists(self, user_id: UUID) -> bool:
        self.calls.append(user_id)
        if self.unavailable:
            from projects_service.src.infrastructure.exceptions import ExternalServiceUnavailable

            raise ExternalServiceUnavailable("auth is down")
        return user_id in self.existing_users


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


@pytest.fixture
def user_id() -> UUID:
    return uuid4()


@pytest.fixture
def another_user_id() -> UUID:
    return uuid4()


@pytest.fixture
def third_user_id() -> UUID:
    return uuid4()


@pytest.fixture
def users_gateway(user_id: UUID, another_user_id: UUID, third_user_id: UUID) -> FakeUsersGateway:
    gateway = FakeUsersGateway()
    gateway.existing_users.update({user_id, another_user_id, third_user_id})
    return gateway


@pytest.fixture
def auth_as(user_id: UUID):
    def switch(current_user_id: UUID = user_id) -> None:
        app.dependency_overrides[get_current_user_id] = lambda: current_user_id
        app.dependency_overrides[get_optional_user_id] = lambda: current_user_id

    return switch


@pytest_asyncio.fixture
async def client(
    db_session: AsyncSession,
    users_gateway: FakeUsersGateway,
    auth_as,
) -> AsyncGenerator[AsyncClient, None]:
    app.dependency_overrides[get_async_session] = lambda: db_session
    app.dependency_overrides[get_users_gateway] = lambda: users_gateway
    auth_as()

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        yield ac

    app.dependency_overrides.clear()
