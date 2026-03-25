from unittest.mock import AsyncMock
from uuid import uuid4

import pytest
from fastapi import HTTPException

from projects_service.src.application.invite_service import InviteService
from projects_service.src.infrastructure.models import ProjectInviteType, RequestStatus, StaffRole


@pytest.fixture
def repo_mock():
    return AsyncMock()


@pytest.fixture
def service(repo_mock):
    return InviteService(repo_mock)


@pytest.mark.asyncio
async def test_send_invite_forbidden(service, repo_mock):
    repo_mock.get_user_role.return_value = StaffRole.PARTICIPANT

    with pytest.raises(HTTPException) as exc:
        await service.send_invite(uuid4(), uuid4(), uuid4())

    assert exc.value.status_code == 403


@pytest.mark.asyncio
async def test_send_invite_already_exists(service, repo_mock):
    repo_mock.get_user_role.side_effect = [
        StaffRole.ADMIN,
        None
    ]
    repo_mock.exists_invite_or_request.return_value = True

    with pytest.raises(HTTPException) as exc:
        await service.send_invite(uuid4(), uuid4(), uuid4())

    assert exc.value.status_code == 409


@pytest.mark.asyncio
async def test_send_invite_success(service, repo_mock):
    repo_mock.get_user_role.side_effect = [
        StaffRole.ADMIN,
        None
    ]
    repo_mock.exists_invite_or_request.return_value = False

    await service.send_invite(uuid4(), uuid4(), uuid4())

    repo_mock.add_invite.assert_called_once()


@pytest.mark.asyncio
async def test_join_request_already_member(service, repo_mock):
    repo_mock.get_user_role.return_value = StaffRole.ADMIN

    with pytest.raises(HTTPException) as exc:
        await service.send_join_request(uuid4(), uuid4())

    assert exc.value.status_code == 409


@pytest.mark.asyncio
async def test_join_request_success(service, repo_mock):
    repo_mock.get_user_role.return_value = None
    repo_mock.exists_invite_or_request.return_value = False
    repo_mock.add_request.return_value = uuid4()

    result = await service.send_join_request(uuid4(), uuid4())

    assert "request_id" in result


@pytest.mark.asyncio
async def test_accept_invite_wrong_user(service, repo_mock):
    invite = AsyncMock(
        type=ProjectInviteType.INVITE,
        project_id=uuid4(),
        target_user_id=uuid4(),
        status=RequestStatus.PENDING
    )

    repo_mock.get_invitation_by_id.return_value = invite

    with pytest.raises(HTTPException) as exc:
        await service.accept_invite_to_join(
            invite.project_id,
            uuid4(),
            uuid4()
        )

    assert exc.value.status_code == 403


@pytest.mark.asyncio
async def test_accept_invite_success(service, repo_mock):
    user_id = uuid4()

    invite = AsyncMock(
        type=ProjectInviteType.INVITE,
        project_id=uuid4(),
        target_user_id=user_id,
        status=RequestStatus.PENDING
    )

    repo_mock.get_invitation_by_id.return_value = invite
    repo_mock.get_user_role.return_value = None

    result = await service.accept_invite_to_join(
        invite.project_id,
        uuid4(),
        user_id
    )

    assert "joined" in result["detail"]


@pytest.mark.asyncio
async def test_reject_request_forbidden(service, repo_mock):
    repo_mock.get_user_role.return_value = StaffRole.PARTICIPANT

    with pytest.raises(HTTPException) as exc:
        await service.reject_join_request(uuid4(), uuid4(), uuid4())

    assert exc.value.status_code == 403
