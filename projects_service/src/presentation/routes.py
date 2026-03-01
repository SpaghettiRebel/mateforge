from fastapi import APIRouter, Depends
from uuid import UUID
from typing import Union, List

from projects_service.src.application.service import ProjectService
from projects_service.src.presentation.dependencies import get_current_user_id, get_optional_user_id, get_service
from projects_service.src.presentation.schemas import ProjectCreateSchema, ProjectPublicSchema, ProjectFullSchema, \
    ProjectUpdateSchema

router = APIRouter()


@router.patch('/{project_id}', response_model=ProjectFullSchema)
async def update_project(
        project_id: UUID,
        project_data: ProjectUpdateSchema,
        current_user_id: UUID = Depends(get_current_user_id),
        service: ProjectService = Depends(get_service),
):
    return await service.update_project(project_id, project_data, current_user_id)

@router.delete('/{project_id}', status_code=204)
async def delete_project(
        project_id: UUID,
        current_user_id: UUID = Depends(get_current_user_id),
        service: ProjectService = Depends(get_service),
):
    return await service.delete_project(project_id, current_user_id)


@router.get('/', response_model=List[Union[ProjectFullSchema, ProjectPublicSchema]])
async def get_user_projects(
        user_id: UUID,
        current_user_id: UUID | None = Depends(get_optional_user_id),
        service: ProjectService = Depends(get_service),
):
    return await service.get_user_projects(user_id, current_user_id)


@router.get('/{project_id}', response_model=Union[ProjectFullSchema, ProjectPublicSchema])
async def get_project(
        project_id: UUID,
        current_user_id: UUID | None = Depends(get_optional_user_id),
        service: ProjectService = Depends(get_service),
):
    return await service.get_project(project_id, current_user_id)


@router.post('/', status_code=201)
async def create_project(
        project_data: ProjectCreateSchema,
        current_user_id: UUID = Depends(get_current_user_id),
        service: ProjectService = Depends(get_service),
) -> ProjectFullSchema:
    return await service.create_project(project_data, current_user_id)
