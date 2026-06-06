from uuid import UUID

import pytest
from sqlalchemy import inspect

from projects_service.src.infrastructure.models import Project, Staff, StaffRole
from projects_service.tests.helpers import create_project


@pytest.mark.asyncio
async def test_projects_migrations_create_expected_schema(db_session):
    def inspect_schema(connection):
        inspector = inspect(connection)
        return {
            "tables": set(inspector.get_table_names()),
            "project_invitation_indexes": {
                item["name"] for item in inspector.get_indexes("project_invitations")
            },
        }

    connection = await db_session.connection()
    schema = await connection.run_sync(inspect_schema)

    assert {
        "projects",
        "staff",
        "project_invitations",
        "tags",
        "project_tags_association",
        "subscriptions",
        "publications",
        "publication_files",
        "alembic_version",
    } <= schema["tables"]
    assert "uq_pending_project_invitation" in schema["project_invitation_indexes"]


@pytest.mark.asyncio
async def test_create_project_persists_founder_staff(client, db_session, user_id):
    project = await create_project(client, name="Open RPG", is_private=True)
    project_id = UUID(project["id"])

    stored_project = await db_session.get(Project, project_id)
    founder = await db_session.get(Staff, {"project_id": project_id, "user_id": user_id})

    assert stored_project.founder_id == user_id
    assert founder.role == StaffRole.FOUNDER


@pytest.mark.asyncio
async def test_private_project_returns_public_shape_to_non_member(client, auth_as, another_user_id):
    project = await create_project(client, name="Secret Project", is_private=True)
    auth_as(another_user_id)

    response = await client.get(f"/projects/{project['id']}")

    assert response.status_code == 200
    assert response.json()["name"] == "Secret Project"
    assert "about" not in response.json()
    assert "founder_id" not in response.json()


@pytest.mark.asyncio
async def test_public_project_returns_full_shape_to_anonymous_user(client, auth_as):
    project = await create_project(client, name="Public Project", is_private=False)
    app_userless = None
    auth_as(app_userless)

    response = await client.get(f"/projects/{project['id']}")

    assert response.status_code == 200
    assert response.json()["about"] == "About the project"


@pytest.mark.asyncio
async def test_update_project_requires_admin_or_founder(client, auth_as, another_user_id):
    project = await create_project(client)
    auth_as(another_user_id)

    forbidden = await client.patch(
        f"/projects/{project['id']}",
        json={"name": "Stolen"},
    )
    assert forbidden.status_code == 403

    auth_as()
    updated = await client.patch(
        f"/projects/{project['id']}",
        json={"name": "Renamed", "about": None, "is_private": False},
    )
    assert updated.status_code == 200
    assert updated.json()["name"] == "Renamed"
    assert updated.json()["about"] is None


@pytest.mark.asyncio
async def test_founder_can_delete_project_but_member_cannot(client, auth_as, another_user_id, db_session):
    project = await create_project(client)

    auth_as(another_user_id)
    forbidden = await client.delete(f"/projects/{project['id']}")
    assert forbidden.status_code == 403

    auth_as()
    deleted = await client.delete(f"/projects/{project['id']}")
    assert deleted.status_code == 204
    assert await db_session.get(Project, UUID(project["id"])) is None


@pytest.mark.asyncio
async def test_member_role_change_persists_and_forbids_founder_role(client, auth_as, another_user_id, db_session):
    project = await create_project(client)
    project_id = UUID(project["id"])
    await client.post(f"/projects/{project['id']}/invite", params={"target_user_id": str(another_user_id)})

    auth_as(another_user_id)
    invite = (await client.get("/projects/invite/all")).json()[0]
    accepted = await client.post(f"/projects/{project['id']}/invite/{invite['id']}/accept")
    assert accepted.status_code == 200

    auth_as()
    changed = await client.patch(
        f"/projects/{project['id']}/staff/{another_user_id}",
        params={"new_role": StaffRole.MANAGER.value},
    )
    assert changed.status_code == 200

    member = await db_session.get(Staff, {"project_id": project_id, "user_id": another_user_id})
    assert member.role == StaffRole.MANAGER.value

    grant_founder = await client.patch(
        f"/projects/{project['id']}/staff/{another_user_id}",
        params={"new_role": StaffRole.FOUNDER.value},
    )
    assert grant_founder.status_code == 403


@pytest.mark.asyncio
async def test_founder_role_cannot_be_changed_or_removed(client, user_id):
    project = await create_project(client)

    change_founder = await client.patch(
        f"/projects/{project['id']}/staff/{user_id}",
        params={"new_role": StaffRole.ADMIN.value},
    )
    assert change_founder.status_code == 403

    kick_founder = await client.delete(f"/projects/{project['id']}/staff/{user_id}")
    assert kick_founder.status_code == 400


@pytest.mark.asyncio
async def test_higher_or_equal_role_cannot_be_kicked(client, auth_as, another_user_id, third_user_id):
    project = await create_project(client)

    for target_user_id in [another_user_id, third_user_id]:
        await client.post(f"/projects/{project['id']}/invite", params={"target_user_id": str(target_user_id)})
        auth_as(target_user_id)
        invite = (await client.get("/projects/invite/all")).json()[0]
        await client.post(f"/projects/{project['id']}/invite/{invite['id']}/accept")
        auth_as()

    await client.patch(
        f"/projects/{project['id']}/staff/{another_user_id}",
        params={"new_role": StaffRole.ADMIN.value},
    )
    await client.patch(
        f"/projects/{project['id']}/staff/{third_user_id}",
        params={"new_role": StaffRole.MANAGER.value},
    )

    auth_as(third_user_id)
    forbidden = await client.delete(f"/projects/{project['id']}/staff/{another_user_id}")
    assert forbidden.status_code == 403


@pytest.mark.asyncio
async def test_get_project_staff_requires_membership(client, auth_as, another_user_id):
    project = await create_project(client)
    auth_as(another_user_id)

    response = await client.get(f"/projects/{project['id']}/staff")

    assert response.status_code == 403
