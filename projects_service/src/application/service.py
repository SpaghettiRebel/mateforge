from uuid import UUID

from projects_service.src.infrastructure.repositories.project_repository import ProjectRepository
from projects_service.src.presentation.schemas import ProjectCreateSchema


class ProjectService:
    def __init__(self, project_repository: ProjectRepository):
        self.project_repository = project_repository

    async def create_project(self, project_data: ProjectCreateSchema, user_id: UUID):
        #TODO: реализовать логику с помощью репозитория
        return {'msg': 'Project was created successfully'}
