import os
from typing import AsyncGenerator
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

from projects_service.src.application.invite_service import InviteService
from projects_service.src.application.projects_managing_service import ProjectService
from projects_service.src.infrastructure.database import Base, get_async_session
from projects_service.src.infrastructure.repositories.project_repository import ProjectRepository
from projects_service.src.main import app
from projects_service.src.presentation.dependencies import get_invite_service, get_project_service

DATABASE_URL = os.getenv("DATABASE_URL")
engine = create_async_engine(DATABASE_URL, echo=False, poolclass=NullPool)

@pytest_asyncio.fixture(scope="session", autouse=True)
async def prepare_database():

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


@pytest_asyncio.fixture()
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


@pytest_asyncio.fixture
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

    monkeypatch.setattr(
        "projects_service.src.presentation.dependencies.get_current_user_id",
        lambda: user_id
    )

    monkeypatch.setattr(
        "projects_service.src.presentation.dependencies.get_optional_user_id",
        lambda: user_id
    )


@pytest_asyncio.fixture(autouse=True)
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
