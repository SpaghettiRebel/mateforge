from fastapi import APIRouter, Depends, Query, Request
from uuid import UUID
from typing import Union, List

from projects_service.src.application.projects_managing_service import ProjectService
from projects_service.src.application.invite_service import InviteService
from projects_service.src.presentation.dependencies import (get_current_user_id, get_optional_user_id,
                                                            get_project_service, get_invite_service)
from projects_service.src.presentation.schemas import (ProjectCreateSchema, ProjectPublicSchema, ProjectFullSchema,
                                                       ProjectUpdateSchema)

router = APIRouter()

@router.post('/{project_id}/invite', status_code=201)
async def send_invite_to_project(
        target_user_id: UUID,
        project_id: UUID,
        current_user_id: UUID = Depends(get_current_user_id),
        service: InviteService = Depends(get_invite_service),
):
    return await service.send_invite(project_id, target_user_id, current_user_id)

@router.post('/{project_id}/invite/{invite_id}/accept', status_code=201)
async def accept_invite_to_project(
        project_id: UUID,
        invite_id: UUID,
        current_user_id: UUID = Depends(get_current_user_id),
        service: InviteService = Depends(get_invite_service),
):
    return await service.accept_invite_to_join(project_id, invite_id, current_user_id)

@router.post('/{project_id}/invite/{invite_id}/reject', status_code=201)
async def reject_invite_to_project(
        project_id: UUID,
        invite_id: UUID,
        current_user_id: UUID = Depends(get_current_user_id),
        service: InviteService = Depends(get_invite_service),
):
    return await service.reject_invite_to_join(project_id, invite_id, current_user_id)

@router.post('/{project_id}/request', status_code=201)
async def send_request_to_project(
        project_id: UUID,
        current_user_id: UUID = Depends(get_current_user_id),
        service: InviteService = Depends(get_invite_service),
):
    return await service.send_join_request(project_id, current_user_id)

@router.post('/{project_id}/request/{request_id}/accept', status_code=201)
async def accept_request_to_project(
        project_id: UUID,
        request_id: UUID,
        request: Request,
        current_user_id: UUID = Depends(get_current_user_id),
        service: InviteService = Depends(get_invite_service),
):
    grpc_client = request.app.state.grpc_client

    return await service.accept_join_request(project_id, request_id, current_user_id, grpc_client)

@router.post('/{project_id}/request/{request_id}/reject', status_code=201)
async def reject_request_to_project(
        project_id: UUID,
        request_id: UUID,
        request: Request,
        current_user_id: UUID = Depends(get_current_user_id),
        service: InviteService = Depends(get_invite_service),
):
    return await service.reject_join_request(project_id, request_id, current_user_id)

@router.patch('/{project_id}', response_model=ProjectFullSchema)
async def update_project(
        project_id: UUID,
        project_data: ProjectUpdateSchema,
        current_user_id: UUID = Depends(get_current_user_id),
        service: ProjectService = Depends(get_project_service),
):
    return await service.update_project(project_id, project_data, current_user_id)

@router.delete('/{project_id}', status_code=204)
async def delete_project(
        project_id: UUID,
        current_user_id: UUID = Depends(get_current_user_id),
        service: ProjectService = Depends(get_project_service),
):
    return await service.delete_project(project_id, current_user_id)


@router.get('/', response_model=List[Union[ProjectFullSchema, ProjectPublicSchema]])
async def get_user_projects(
        user_id: UUID,
        current_user_id: UUID | None = Depends(get_optional_user_id),
        service: ProjectService = Depends(get_project_service),
):
    return await service.get_user_projects(user_id, current_user_id)


@router.get('/{project_id}', response_model=Union[ProjectFullSchema, ProjectPublicSchema])
async def get_project(
        project_id: UUID,
        current_user_id: UUID | None = Depends(get_optional_user_id),
        service: ProjectService = Depends(get_project_service),
):
    return await service.get_project(project_id, current_user_id)


@router.post('/', status_code=201)
async def create_project(
        project_data: ProjectCreateSchema,
        current_user_id: UUID = Depends(get_current_user_id),
        service: ProjectService = Depends(get_project_service),
) -> ProjectFullSchema:
    return await service.create_project(project_data, current_user_id)
