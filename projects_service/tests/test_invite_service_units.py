from uuid import uuid4

import pytest
from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from projects_service.src.application.invite_service import InviteService
from projects_service.src.application.projects_managing_service import ProjectService
from projects_service.src.infrastructure.models import (
    ProjectInvitation,
    ProjectInviteType,
    RequestStatus,
    StaffRole,
)
from projects_service.src.infrastructure.repositories.project_repository import ProjectRepository
from projects_service.src.presentation.schemas import ProjectCreateSchema


@pytest.mark.asyncio
async def test_invite_service_direct_success_and_conflict_paths(db_session, users_gateway, user_id, another_user_id):
    repository = ProjectRepository(db_session)
    project_service = ProjectService(repository)
    invite_service = InviteService(repository, users_gateway)
    project = await project_service.create_project(
        ProjectCreateSchema(name="Invites", about="Invite checks", is_private=False),
        user_id,
    )

    sent = await invite_service.send_invite(project.id, another_user_id, user_id)
    assert sent == {"detail": "Invitation sent"}

    with pytest.raises(HTTPException) as duplicate_invite:
        await invite_service.send_invite(project.id, another_user_id, user_id)
    assert duplicate_invite.value.status_code == 409

    invitation = (await db_session.execute(select(ProjectInvitation))).scalar_one()
    with pytest.raises(HTTPException) as wrong_project:
        await invite_service.accept_invite_to_join(uuid4(), invitation.id, another_user_id)
    assert wrong_project.value.status_code == 400

    joined = await invite_service.accept_invite_to_join(project.id, invitation.id, another_user_id)
    assert joined == {"detail": "You have successfully joined the project"}

    with pytest.raises(HTTPException) as member_exists:
        await invite_service.send_invite(project.id, another_user_id, user_id)
    assert member_exists.value.status_code == 409

    with pytest.raises(HTTPException) as request_from_member:
        await invite_service.send_join_request(project.id, another_user_id)
    assert request_from_member.value.status_code == 409


@pytest.mark.asyncio
async def test_invite_service_join_request_management_paths(db_session, users_gateway, user_id, another_user_id):
    repository = ProjectRepository(db_session)
    project_service = ProjectService(repository)
    invite_service = InviteService(repository, users_gateway)
    project = await project_service.create_project(
        ProjectCreateSchema(name="Requests", about="Request checks", is_private=False),
        user_id,
    )

    request = await invite_service.send_join_request(project.id, another_user_id)
    assert request["request_id"]

    with pytest.raises(HTTPException) as duplicate_request:
        await invite_service.send_join_request(project.id, another_user_id)
    assert duplicate_request.value.status_code == 409

    await repository.add_to_staff(project.id, another_user_id, StaffRole.PARTICIPANT)
    await repository.commit()

    accepted_existing = await invite_service.accept_join_request(project.id, request["request_id"], user_id)
    assert accepted_existing == {"detail": "User is already in staff"}

    join_request = await db_session.get(ProjectInvitation, request["request_id"])
    assert join_request.status == RequestStatus.ACCEPTED

    fresh_user = uuid4()
    users_gateway.existing_users.add(fresh_user)
    fresh_request = await invite_service.send_join_request(project.id, fresh_user)
    rejected = await invite_service.reject_join_request(project.id, fresh_request["request_id"], user_id)
    assert rejected == {"detail": "Join request rejected"}

    with pytest.raises(HTTPException) as already_processed:
        await invite_service.accept_join_request(project.id, fresh_request["request_id"], user_id)
    assert already_processed.value.status_code == 409


@pytest.mark.asyncio
async def test_invite_service_missing_project_gateway_and_integrity_branches(
    db_session,
    users_gateway,
    user_id,
    another_user_id,
):
    repository = ProjectRepository(db_session)
    invite_service = InviteService(repository, users_gateway)

    with pytest.raises(HTTPException) as missing_project:
        await invite_service.send_invite(uuid4(), another_user_id, user_id)
    assert missing_project.value.status_code == 404

    project = await ProjectService(repository).create_project(
        ProjectCreateSchema(name="Gateway", about="Gateway checks", is_private=False),
        user_id,
    )

    users_gateway.unavailable = True
    with pytest.raises(HTTPException) as unavailable:
        await invite_service.send_invite(project.id, another_user_id, user_id)
    assert unavailable.value.status_code == 503
    users_gateway.unavailable = False

    users_gateway.existing_users.remove(another_user_id)
    with pytest.raises(HTTPException) as missing_user:
        await invite_service.send_invite(project.id, another_user_id, user_id)
    assert missing_user.value.status_code == 404


@pytest.mark.asyncio
async def test_invite_service_rolls_back_on_repository_integrity_error(users_gateway, user_id, another_user_id):
    class IntegrityRepository:
        rolled_back = False

        async def get_by_id(self, project_id):
            return object()

        async def get_user_role(self, project_id, requested_user_id):
            if requested_user_id == user_id:
                return StaffRole.ADMIN
            return None

        async def exists_invite_or_request(self, project_id, requested_user_id, status=RequestStatus.PENDING):
            return False

        async def add_invite(self, project_id, target_user_id, current_user_id):
            raise IntegrityError("insert", {}, Exception("duplicate"))

        async def commit(self):
            raise AssertionError("commit should not run after failed insert")

        async def rollback(self):
            self.rolled_back = True

    repository = IntegrityRepository()
    service = InviteService(repository, users_gateway)

    with pytest.raises(HTTPException) as conflict:
        await service.send_invite(uuid4(), another_user_id, user_id)

    assert conflict.value.status_code == 409
    assert repository.rolled_back is True


@pytest.mark.asyncio
async def test_invite_service_private_add_member_integrity_guard(users_gateway):
    class IntegrityRepository:
        rolled_back = False

        async def add_to_staff(self, project_id, user_id, role=StaffRole.PARTICIPANT):
            raise IntegrityError("insert", {}, Exception("duplicate staff"))

        async def commit(self):
            raise AssertionError("commit should not run after failed staff insert")

        async def rollback(self):
            self.rolled_back = True

    invitation = ProjectInvitation(
        id=uuid4(),
        project_id=uuid4(),
        user_id=uuid4(),
        sender_id=uuid4(),
        type=ProjectInviteType.INVITE,
    )
    repository = IntegrityRepository()
    service = InviteService(repository, users_gateway)

    with pytest.raises(HTTPException) as conflict:
        await service._add_member_from_invitation(invitation)

    assert conflict.value.status_code == 409
    assert repository.rolled_back is True
