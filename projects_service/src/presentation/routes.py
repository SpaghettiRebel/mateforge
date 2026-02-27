from fastapi import APIRouter, Depends
from uuid import UUID
from typing import Union

from projects_service.src.application.service import ProjectService
from projects_service.src.presentation.dependencies import get_current_user_id, get_service
from projects_service.src.presentation.schemas import ProjectCreateSchema, ProjectFullSchema, ProjectPublicSchema

router = APIRouter()

@router.get('/', response_model='Union[ProjectFullSchema, ProjectPublicSchema]')
async def get_project(
        project_id: UUID,
        user_id: UUID = Depends(get_current_user_id),
        service: ProjectService = Depends(get_service),
):
    return await service.get_project(project_id, user_id)

@router.post('/', status_code=201)
async def create_project(
        project_data: ProjectCreateSchema,
        user_id: UUID = Depends(get_current_user_id),
        service: ProjectService = Depends(get_service),
) -> dict:
    return await service.create_project(project_data, user_id)
