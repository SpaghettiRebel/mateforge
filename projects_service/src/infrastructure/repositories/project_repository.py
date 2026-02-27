from sqlalchemy.ext.asyncio import AsyncSession

from projects_service.src.infrastructure.models import Project, Staff, StaffRole
from projects_service.src.presentation.schemas import ProjectCreateSchema


class ProjectRepository:
    def __init__(self, session: AsyncSession):
        self.session = session


    async def create_instance(self, project_data: ProjectCreateSchema, founder_id) -> Project:
        new_project = Project(founder_id=founder_id,
                              name=project_data.name,
                              about=project_data.about,
                              is_private=project_data.is_private)
        return new_project

    async def add_project(self, project: Project) -> Project:
        founder_as_staff = Staff(
            user_id=project.founder_id,
            role=StaffRole.FOUNDER
        )

        project.staff.append(founder_as_staff)

        self.session.add(project)
        await self.session.flush()

        return project


