from uuid import UUID

import pytest
from sqlalchemy import select

from projects_service.src.infrastructure.models import ProjectInvitation, RequestStatus, Staff, StaffRole
from projects_service.tests.helpers import create_project


@pytest.mark.asyncio
async def test_send_invite_checks_target_user_exists(client, users_gateway, another_user_id):
    project = await create_project(client)
    users_gateway.existing_users.remove(another_user_id)

    response = await client.post(
        f"/projects/{project['id']}/invite",
        params={"target_user_id": str(another_user_id)},
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "User not found"
    assert users_gateway.calls == [another_user_id]


@pytest.mark.asyncio
async def test_send_invite_returns_503_when_auth_gateway_is_unavailable(client, users_gateway, another_user_id):
    project = await create_project(client)
    users_gateway.unavailable = True

    response = await client.post(
        f"/projects/{project['id']}/invite",
        params={"target_user_id": str(another_user_id)},
    )

    assert response.status_code == 503


@pytest.mark.asyncio
async def test_invite_accept_and_reject_are_user_scoped(client, auth_as, another_user_id, third_user_id, db_session):
    project = await create_project(client)
    project_id = UUID(project["id"])
    invite_response = await client.post(
        f"/projects/{project['id']}/invite",
        params={"target_user_id": str(another_user_id)},
    )
    assert invite_response.status_code == 201

    duplicate = await client.post(
        f"/projects/{project['id']}/invite",
        params={"target_user_id": str(another_user_id)},
    )
    assert duplicate.status_code == 409

    auth_as(third_user_id)
    foreign_invite = (await db_session.execute(select(ProjectInvitation))).scalar_one()
    wrong_user = await client.post(f"/projects/{project['id']}/invite/{foreign_invite.id}/accept")
    assert wrong_user.status_code == 403

    auth_as(another_user_id)
    accepted = await client.post(f"/projects/{project['id']}/invite/{foreign_invite.id}/accept")
    assert accepted.status_code == 200

    member = await db_session.get(Staff, {"project_id": project_id, "user_id": another_user_id})
    assert member.role == StaffRole.PARTICIPANT.value

    replay = await client.post(f"/projects/{project['id']}/invite/{foreign_invite.id}/accept")
    assert replay.status_code == 409


@pytest.mark.asyncio
async def test_reject_invite_updates_status_and_prevents_accept(client, auth_as, another_user_id, db_session):
    project = await create_project(client)
    await client.post(f"/projects/{project['id']}/invite", params={"target_user_id": str(another_user_id)})
    invite = (await db_session.execute(select(ProjectInvitation))).scalar_one()

    auth_as(another_user_id)
    rejected = await client.post(f"/projects/{project['id']}/invite/{invite.id}/reject")
    assert rejected.status_code == 200

    await db_session.refresh(invite)
    assert invite.status == RequestStatus.REJECTED

    accept_after_reject = await client.post(f"/projects/{project['id']}/invite/{invite.id}/accept")
    assert accept_after_reject.status_code == 409


@pytest.mark.asyncio
async def test_join_request_acceptance_checks_user_and_adds_staff(client, auth_as, another_user_id, db_session):
    project = await create_project(client)
    project_id = UUID(project["id"])

    auth_as(another_user_id)
    request_response = await client.post(f"/projects/{project['id']}/request")
    assert request_response.status_code == 201

    auth_as()
    accepted = await client.post(
        f"/projects/{project['id']}/request/{request_response.json()['request_id']}/accept"
    )
    assert accepted.status_code == 200

    member = await db_session.get(Staff, {"project_id": project_id, "user_id": another_user_id})
    assert member.role == StaffRole.PARTICIPANT.value


@pytest.mark.asyncio
async def test_join_request_for_deleted_user_is_rejected(client, auth_as, users_gateway, another_user_id, db_session):
    project = await create_project(client)

    auth_as(another_user_id)
    request_response = await client.post(f"/projects/{project['id']}/request")
    request_id = request_response.json()["request_id"]
    users_gateway.existing_users.remove(another_user_id)

    auth_as()
    accepted = await client.post(f"/projects/{project['id']}/request/{request_id}/accept")
    assert accepted.status_code == 404

    invitation = await db_session.get(ProjectInvitation, request_id)
    assert invitation.status == RequestStatus.REJECTED


@pytest.mark.asyncio
async def test_participant_cannot_manage_join_requests(client, auth_as, another_user_id, third_user_id):
    project = await create_project(client)
    await client.post(f"/projects/{project['id']}/invite", params={"target_user_id": str(another_user_id)})

    auth_as(another_user_id)
    invite = (await client.get("/projects/invite/all")).json()[0]
    await client.post(f"/projects/{project['id']}/invite/{invite['id']}/accept")

    auth_as(third_user_id)
    request_response = await client.post(f"/projects/{project['id']}/request")
    request_id = request_response.json()["request_id"]

    auth_as(another_user_id)
    forbidden = await client.post(f"/projects/{project['id']}/request/{request_id}/accept")
    assert forbidden.status_code == 403


@pytest.mark.asyncio
async def test_user_invites_and_requests_lists_return_only_current_user(client, auth_as, another_user_id, third_user_id):
    project = await create_project(client)
    await client.post(f"/projects/{project['id']}/invite", params={"target_user_id": str(another_user_id)})

    auth_as(third_user_id)
    await client.post(f"/projects/{project['id']}/request")
    assert (await client.get("/projects/invite/all")).json() == []
    assert len((await client.get("/projects/request/all")).json()) == 1

    auth_as(another_user_id)
    invites = (await client.get("/projects/invite/all")).json()
    requests = (await client.get("/projects/request/all")).json()

    assert len(invites) == 1
    assert requests == []
