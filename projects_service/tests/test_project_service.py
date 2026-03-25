from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest
from fastapi import HTTPException

from projects_service.src.application.projects_managing_service import ProjectService
from projects_service.src.infrastructure.models import StaffRole


@pytest.fixture
def repo_mock():
    return AsyncMock()


@pytest.fixture
def service(repo_mock):
    return ProjectService(repo_mock)


@pytest.mark.asyncio
async def test_create_project_success(service, repo_mock):
    user_id = uuid4()
    project_id = uuid4()

    project = MagicMock()
    project.id = project_id
    project.name = "Test Project"
    project.avatar_path = "path/to/avatar"
    project.banner_path = "path/to/banner"
    project.founder_id = user_id
    project.about = "Description"
    project.is_private = False

    repo_mock.create_project_instance.return_value = project

    result = await service.create_project({}, user_id)
    assert result.name == "Test Project"


@pytest.mark.asyncio
async def test_get_project_not_found(service, repo_mock):
    repo_mock.get_by_id.return_value = None

    with pytest.raises(HTTPException) as exc:
        await service.get_project(uuid4())

    assert exc.value.status_code == 404


@pytest.mark.asyncio
async def test_get_private_project_no_user(service, repo_mock):
    project = MagicMock()
    project.id = uuid4()
    project.name = "Private Project"
    project.avatar_path = "avatar.png"
    project.banner_path = "banner.png"
    project.is_private = True

    repo_mock.get_by_id.return_value = project

    result = await service.get_project(project.id, None)

    assert result.name == "Private Project"
    assert result.id == project.id


@pytest.mark.asyncio
async def test_delete_project_not_founder(service, repo_mock):
    user_id = uuid4()
    project = AsyncMock(founder_id=uuid4())

    repo_mock.get_by_id.return_value = project

    with pytest.raises(HTTPException) as exc:
        await service.delete_project(uuid4(), user_id)

    assert exc.value.status_code == 403


@pytest.mark.asyncio
async def test_update_project_forbidden(service, repo_mock):
    project = AsyncMock()
    repo_mock.get_by_id.return_value = project
    repo_mock.get_user_role.return_value = StaffRole.PARTICIPANT

    with pytest.raises(HTTPException) as exc:
        await service.update_project(uuid4(), {}, uuid4())

    assert exc.value.status_code == 403


@pytest.mark.asyncio
async def test_leave_project(service, repo_mock):
    user_id = uuid4()

    repo_mock.get_by_id.return_value = AsyncMock()
    repo_mock.get_user_role.side_effect = [
        StaffRole.ADMIN,   # current
        StaffRole.ADMIN    # target
    ]

    result = await service.delete_member_from_project(
        uuid4(), user_id, user_id
    )

    assert result["detail"] == "You left the project"


@pytest.mark.asyncio
async def test_kick_higher_role_forbidden(service, repo_mock):
    repo_mock.get_by_id.return_value = AsyncMock()
    repo_mock.get_user_role.side_effect = [
        StaffRole.MANAGER,
        StaffRole.ADMIN
    ]

    with pytest.raises(HTTPException) as exc:
        await service.delete_member_from_project(
            uuid4(), uuid4(), uuid4()
        )

    assert exc.value.status_code == 403


@pytest.mark.asyncio
async def test_change_role_success(service, repo_mock):
    repo_mock.get_by_id.return_value = AsyncMock()
    repo_mock.get_user_role.side_effect = [
        StaffRole.ADMIN,
        StaffRole.PARTICIPANT
    ]

    result = await service.change_member_role(
        uuid4(),
        uuid4(),
        uuid4(),
        StaffRole.MANAGER
    )

    assert "Role updated" in result["detail"]
