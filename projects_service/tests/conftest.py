import pytest
from typing import AsyncGenerator
from uuid import uuid4
from unittest.mock import AsyncMock

from testcontainers.postgres import PostgresContainer

from sqlalchemy.ext.asyncio import (
    create_async_engine,
    async_sessionmaker,
    AsyncSession
)

from httpx import AsyncClient, ASGITransport

from projects_service.src.main import app
from projects_service.src.infrastructure.database import Base, get_async_session
from projects_service.src.presentation.dependencies import (
    get_project_service,
    get_invite_service
)

from projects_service.src.application.projects_managing_service import ProjectService
from projects_service.src.application.invite_service import InviteService
from projects_service.src.infrastructure.repositories.project_repository import ProjectRepository


@pytest.fixture(scope="session")
def postgres_container():
    with PostgresContainer("postgres:15-alpine") as postgres:
        yield postgres


@pytest.fixture(scope="session")
async def db_engine(postgres_container):
    url = postgres_container.get_connection_url().replace("psycopg2", "asyncpg")

    engine = create_async_engine(url, echo=False)

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    yield engine

    await engine.dispose()


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
def project_repository(db_session):
    return ProjectRepository(db_session)


@pytest.fixture
def project_service(project_repository):
    return ProjectService(project_repository)


@pytest.fixture
def invite_service(project_repository):
    return InviteService(project_repository)


@pytest.fixture
def grpc_client_mock():
    mock = AsyncMock()
    mock.GetUserExistence.return_value.exists = True
    return mock


@pytest.fixture
async def client(
    db_session,
    project_service,
    invite_service,
    grpc_client_mock
) -> AsyncGenerator[AsyncClient, None]:

    # dependency overrides
    app.dependency_overrides[get_async_session] = lambda: db_session
    app.dependency_overrides[get_project_service] = lambda: project_service
    app.dependency_overrides[get_invite_service] = lambda: invite_service

    # mock grpc
    app.state.grpc_client = grpc_client_mock

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test"
    ) as ac:
        yield ac

    app.dependency_overrides.clear()


@pytest.fixture
def user_id():
    return uuid4()


@pytest.fixture
def another_user_id():
    return uuid4()


@pytest.fixture(autouse=True)
def mock_auth(monkeypatch, user_id):
    from projects_service.src.presentation.dependencies import get_current_user_id, get_optional_user_id

    monkeypatch.setattr(
        "projects_service.src.presentation.dependencies.get_current_user_id",
        lambda: user_id
    )

    monkeypatch.setattr(
        "projects_service.src.presentation.dependencies.get_optional_user_id",
        lambda: user_id
    )


@pytest.fixture(autouse=True)
async def clear_data(db_session):
    yield
    from sqlalchemy import text

    # порядок важен (FK)
    await db_session.execute(text("DELETE FROM publication_files"))
    await db_session.execute(text("DELETE FROM publications"))
    await db_session.execute(text("DELETE FROM subscriptions"))
    await db_session.execute(text("DELETE FROM project_invitations"))
    await db_session.execute(text("DELETE FROM staff"))
    await db_session.execute(text("DELETE FROM projects"))

    await db_session.commit()