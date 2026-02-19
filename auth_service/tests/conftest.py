import pytest
from unittest.mock import AsyncMock
import asyncio
from typing import AsyncGenerator
from testcontainers.postgres import PostgresContainer
from testcontainers.redis import RedisContainer
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from redis.asyncio import Redis
from httpx import AsyncClient, ASGITransport

from auth_service.src.main import app
from auth_service.src.infrastructure.database import Base, get_async_session
from auth_service.src.infrastructure.redis import get_redis_client


@pytest.fixture(scope="session")
def postgres_container():
    with PostgresContainer("postgres:15-alpine") as postgres:
        yield postgres


@pytest.fixture(scope="session")
def redis_container():
    with RedisContainer("redis:7-alpine") as redis:
        yield redis


@pytest.fixture(scope="session")
async def db_engine(postgres_container):
    url = postgres_container.get_connection_url().replace("psycopg2", "asyncpg")

    engine = create_async_engine(url, echo=False)

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    yield engine

    await engine.dispose()


@pytest.fixture(scope="session")
async def redis_client_session(redis_container):
    port = redis_container.get_exposed_port(6379)
    host = redis_container.get_container_host_ip()

    client = Redis(host=host, port=port, decode_responses=True)
    yield client
    await client.aclose()


@pytest.fixture
async def db_session(db_engine) -> AsyncGenerator[AsyncSession, None]:
    connection = await db_engine.connect()
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
