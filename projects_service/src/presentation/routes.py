from fastapi import APIRouter, Depends
from uuid import UUID

from projects_service.src.application.service import ProjectService
from projects_service.src.presentation.dependencies import get_current_user_id, get_service
from projects_service.src.presentation.schemas import ProjectCreateSchema

router = APIRouter()

@router.get('/')
async def create_project():
    return {'result': 'OK (not implemented yet)'}

@router.post('/', status_code=201)
async def create_project(
        project_data: ProjectCreateSchema,
        user_id: UUID = Depends(get_current_user_id),
        service: ProjectService = Depends(get_service)
) -> dict:
    return await service.create_project(project_data, user_id)
