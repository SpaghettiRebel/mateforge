from uuid import UUID
from fastapi import HTTPException, status

from projects_service.src.infrastructure.models import StaffRole
from projects_service.src.infrastructure.repositories.project_repository import ProjectRepository
from projects_service.src.presentation.schemas import ProjectCreateSchema, ProjectPublicSchema, ProjectFullSchema, \
    ProjectUpdateSchema


class ProjectService:
    def __init__(self, project_repository: ProjectRepository):
        self.repository = project_repository

    async def create_project(self, project_data: ProjectCreateSchema, user_id: UUID):
        new_project = await self.repository.create_instance(project_data, user_id)

        await self.repository.add(new_project)
        await self.repository.session.commit()
        await self.repository.session.refresh(new_project)

        return ProjectFullSchema.model_validate(new_project)


    async def get_project(self, project_id: UUID, user_id: UUID | None = None):
        project = await self.repository.get_by_id(project_id)
        if not project:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                                detail="Project not found")

        if not project.is_private:
            return ProjectFullSchema.model_validate(project)

        if not user_id:
            return ProjectPublicSchema.model_validate(project)

        user_role = await self.repository.get_user_role(project_id, user_id)

        if not user_role:
            return ProjectPublicSchema.model_validate(project)
        return ProjectFullSchema.model_validate(project)


    async def get_user_projects(self, user_id: UUID, current_user_id: UUID):
        projects_list = await self.repository.get_projects_with_staff_flag(user_id, current_user_id)
        res = []

        for project in projects_list:
            is_staff = getattr(project, "is_staff", False)
            project_data = project[0]

            if not project_data.is_private or is_staff:
                res.append(ProjectFullSchema.model_validate(project_data))
            else:
                res.append(ProjectPublicSchema.model_validate(project_data))

        return res


    async def delete_project(self, project_id: UUID, user_id: UUID):
        project = await self.repository.get_by_id(project_id)
        if not project:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                                detail="Project not found")

        if project.founder_id != user_id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN,
                                detail="Only a creator of the project can delete it")

        await self.repository.delete(project_id)
        await self.repository.session.commit()


    async def update_project(self, project_id: UUID, project_data: ProjectUpdateSchema, user_id: UUID):
        project = await self.repository.get_by_id(project_id)
        if not project:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                                detail="Project not found")

        user_role = await self.repository.get_user_role(project_id, user_id)

        forbidden_roles = (StaffRole.MANAGER, StaffRole.PARTICIPANT)
        if not user_role or user_role in forbidden_roles:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN,
                                detail="You have no rights to change this project's data")

        updated_project = await self.repository.update(project, project_data)

        return ProjectFullSchema.model_validate(updated_project)
