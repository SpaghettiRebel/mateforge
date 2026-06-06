from uuid import uuid4

import pytest
from fastapi import HTTPException

from projects_service.src.application.projects_managing_service import ProjectService
from projects_service.src.infrastructure.models import StaffRole
from projects_service.src.infrastructure.repositories.project_repository import ProjectRepository
from projects_service.src.presentation.schemas import (
    ProjectCreateSchema,
    ProjectFullSchema,
    ProjectPublicSchema,
    ProjectUpdateSchema,
)


@pytest.mark.asyncio
async def test_project_service_exposes_privacy_and_search_document(db_session, user_id, another_user_id):
    repository = ProjectRepository(db_session)
    service = ProjectService(repository)

    created = await service.create_project(
        ProjectCreateSchema(name="Service Project", about="Private notes", is_private=True),
        user_id,
    )

    project = await repository.get_by_id(created.id)
    search_document = service.to_search_document(project)
    anonymous_view = await service.get_project(created.id)
    owner_view = await service.get_project(created.id, user_id)
    user_projects_for_owner = await service.get_user_projects(user_id, user_id)
    user_projects_for_anonymous = await service.get_user_projects(user_id, None)

    assert search_document == {
        "id": str(created.id),
        "title": "Service Project",
        "description": "Private notes",
        "tags": [],
        "tag_groups": {},
        "created_at": project.created_at.timestamp(),
        "owner_id": str(user_id),
    }
    assert isinstance(anonymous_view, ProjectPublicSchema)
    assert isinstance(owner_view, ProjectFullSchema)
    assert owner_view.about == "Private notes"
    assert isinstance(user_projects_for_owner[0], ProjectFullSchema)
    assert isinstance(user_projects_for_anonymous[0], ProjectPublicSchema)

    with pytest.raises(HTTPException) as not_found:
        await service.get_project(uuid4(), user_id)
    assert not_found.value.status_code == 404


@pytest.mark.asyncio
async def test_project_service_role_mutations_and_not_found_branches(db_session, user_id, another_user_id, third_user_id):
    repository = ProjectRepository(db_session)
    service = ProjectService(repository)
    created = await service.create_project(
        ProjectCreateSchema(name="Roles", about="Role checks", is_private=False),
        user_id,
    )

    with pytest.raises(HTTPException) as update_forbidden:
        await service.update_project(created.id, ProjectUpdateSchema(name="Nope"), another_user_id)
    assert update_forbidden.value.status_code == 403

    updated = await service.update_project(
        created.id,
        ProjectUpdateSchema(name="Updated", about=None, is_private=True),
        user_id,
    )
    assert updated.name == "Updated"
    assert updated.about is None

    with pytest.raises(HTTPException) as delete_missing:
        await service.delete_project(uuid4(), user_id)
    assert delete_missing.value.status_code == 404

    await repository.add_to_staff(created.id, another_user_id, StaffRole.PARTICIPANT)
    await repository.commit()

    with pytest.raises(HTTPException) as target_missing:
        await service.delete_member_from_project(created.id, third_user_id, user_id)
    assert target_missing.value.status_code == 404

    left = await service.delete_member_from_project(created.id, another_user_id, another_user_id)
    assert left == {"detail": "You left the project"}

    with pytest.raises(HTTPException) as missing_role_target:
        await service.change_member_role(created.id, third_user_id, user_id, StaffRole.PARTICIPANT)
    assert missing_role_target.value.status_code == 404

    await repository.add_to_staff(created.id, another_user_id, StaffRole.PARTICIPANT)
    await repository.commit()

    with pytest.raises(HTTPException) as over_grant:
        await service.change_member_role(created.id, another_user_id, another_user_id, StaffRole.ADMIN)
    assert over_grant.value.status_code == 403

    changed = await service.change_member_role(created.id, another_user_id, user_id, StaffRole.MANAGER)
    assert changed == {"detail": "Role updated to manager"}

    staff = await service.get_project_staff(created.id, user_id)
    assert {member.user_id for member in staff} == {user_id, another_user_id}

    with pytest.raises(HTTPException) as staff_missing_project:
        await service.get_project_staff(uuid4(), user_id)
    assert staff_missing_project.value.status_code == 404
