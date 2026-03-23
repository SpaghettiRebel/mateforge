from typing import Tuple, List
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete

from projects_service.src.infrastructure.models import Project, Staff, StaffRole, ProjectInvitation, ProjectInviteType, \
    RequestStatus
from projects_service.src.presentation.schemas import ProjectCreateSchema, ProjectUpdateSchema


class ProjectRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    @staticmethod
    async def create_project_instance(project_data: ProjectCreateSchema, founder_id) -> Project:
        new_project = Project(founder_id=founder_id,
                              name=project_data.name,
                              about=project_data.about,
                              is_private=project_data.is_private)
        return new_project

    @staticmethod
    async def create_invitation_instance(
            project_id: UUID,
            user_id: UUID,
            sender_id: UUID,
            invitation_type: ProjectInviteType
    ) -> ProjectInvitation:
        new_invitaion = ProjectInvitation(project_id=project_id,
                              user_id=user_id,
                              sender_id=sender_id,
                              type=invitation_type)
        return new_invitaion

    async def add(self, project: Project) -> Project:
        founder_as_staff = Staff(
            user_id=project.founder_id,
            role=StaffRole.FOUNDER
        )

        project.staff.append(founder_as_staff)

        self.session.add(project)
        await self.session.flush()

        return project

    async def get_by_id(self, project_id: UUID) -> Project | None:
        project = await self.session.get(Project, project_id)
        return project

    async def get_user_role(self, project_id: UUID, user_id: UUID) -> str | None:
        query = select(Staff).where(
            Staff.project_id == project_id,
            Staff.user_id == user_id
        )
        result = await self.session.execute(query)

        staff_member = result.scalar_one_or_none()

        if staff_member:
            return staff_member.role
        return None

    async def delete(self, project_id) -> None:
        query = delete(Project).where(Project.id == project_id)
        await self.session.execute(query)

    async def get_projects_with_staff_flag(self, target_user_id: UUID, current_user_id: UUID | None) -> Tuple[Project, bool]:
        query = select(Project).where(Project.founder_id == target_user_id)

        if current_user_id:
            is_staff_subquery = (
                select(Staff.project_id)
                .where(Staff.project_id == Project.id, Staff.user_id == current_user_id)
                .exists()
            ).label("is_staff")
            query = query.add_columns(is_staff_subquery)

        result = await self.session.execute(query)
        return result.all()

    async def update(self, project: Project, project_data: ProjectUpdateSchema) -> Project:
        update_data = project_data.model_dump(exclude_unset=True)

        for key, value in update_data.items():
            setattr(project, key, value)

        await self.session.commit()
        await self.session.refresh(project)

        return project

    async def add_invite(self, project_id: UUID, target_user_id: UUID, current_user_id: UUID) -> None:
        invite = await self.create_invitation_instance(
            project_id=project_id,
            sender_id=current_user_id,
            user_id=target_user_id,
            invitation_type=ProjectInviteType.INVITE
        )

        self.session.add(invite)
        await self.session.flush()

    async def add_request(self, project_id: UUID, current_user_id: UUID) -> UUID:
        invite = await self.create_invitation_instance(
            project_id=project_id,
            sender_id=current_user_id,
            user_id=current_user_id,
            invitation_type=ProjectInviteType.REQUEST
        )

        self.session.add(invite)
        await self.session.flush()
        await self.session.refresh(invite)

        return invite.id

    async def exists_invite_or_request(
            self,
            project_id: UUID,
            user_id: UUID,
            status: RequestStatus = RequestStatus.PENDING,
    ) -> bool:
        query = (
            select(ProjectInvitation.id)
            .where(
                ProjectInvitation.project_id == project_id,
                ProjectInvitation.user_id == user_id,
                ProjectInvitation.status == status
            )
            .limit(1)
        )
        result = await self.session.execute(query)
        return result.scalar() is not None

    async def get_invitation_by_id(self, invite_id: UUID) -> ProjectInvitation | None:
        query = (
            select(ProjectInvitation)
            .where(ProjectInvitation.id == invite_id)
        )
        result = await self.session.execute(query)
        return result.scalar_one_or_none()

    async def add_to_staff(
            self,
            project_id: UUID,
            user_id: UUID,
            role: StaffRole = StaffRole.PARTICIPANT
    ) -> None:
        new_member = Staff(
            project_id=project_id,
            user_id=user_id,
            role=role.value
        )
        self.session.add(new_member)
        await self.session.flush()

    async def delete_from_staff(self, project_id: UUID, user_id: UUID) -> None:
        query = delete(Staff).where(Staff.project_id == project_id, Staff.user_id == user_id)
        await self.session.execute(query)

    async def update_staff_role(
            self,
            project_id: UUID,
            user_id: UUID,
            new_role: StaffRole = StaffRole.PARTICIPANT
    ) -> None:
        query = select(Staff).where(Staff.project_id == project_id, Staff.user_id == user_id)
        member = await self.session.execute(query)

        member.role = new_role

        await self.session.commit()

    async def get_staff(self, project_id: UUID) -> List[Staff]:
        query = select(Staff).where(Staff.project_id == project_id)
        result = await self.session.execute(query)

        return result.scalars().all()
