from uuid import UUID

from projects_service.src.infrastructure.repositories.project_repository import ProjectRepository
from projects_service.src.presentation.schemas import ProjectCreateSchema


class ProjectService:
    def __init__(self, project_repository: ProjectRepository):
        self.repository = project_repository

    async def create_project(self, project_data: ProjectCreateSchema, user_id: UUID):
        new_project = await self.repository.create_instance(project_data, user_id)

        await self.repository.add_project(new_project)
        await self.repository.session.commit()
        await self.repository.session.refresh(new_project)

        return {'msg': 'Project was created successfully',
                'project_id': new_project.id}

    async def get_project(self, project_id: UUID, user_id: UUID):
        ... # TODO: получить project по id
            # TODO: проверить есть ли user_id в project.staff
            # TODO: выдать либо фулл, либо обрезанную схему
