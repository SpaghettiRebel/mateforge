from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy.exc import IntegrityError

from projects_service.src.application.ports import UsersGateway
from projects_service.src.infrastructure.exceptions import ExternalServiceUnavailable
from projects_service.src.infrastructure.models import (
    ProjectInvitation,
    ProjectInviteType,
    RequestStatus,
    StaffRole,
)
from projects_service.src.infrastructure.repositories.project_repository import ProjectRepository
from projects_service.src.presentation.schemas import ProjectInvitationSchema


class InviteService:
    def __init__(self, project_repository: ProjectRepository, users_gateway: UsersGateway):
        self.repository = project_repository
        self.users_gateway = users_gateway

    async def send_invite(self, project_id: UUID, target_user_id: UUID, current_user_id: UUID):
        await self._get_project_or_404(project_id)

        current_user_role = await self.repository.get_user_role(project_id, current_user_id)
        if not current_user_role or current_user_role == StaffRole.PARTICIPANT:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You have no rights to invite new members to this project",
            )

        target_user_role = await self.repository.get_user_role(project_id, target_user_id)
        if target_user_role:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Member already exists")

        await self._ensure_user_exists(target_user_id)
        await self._ensure_no_pending_invitation(project_id, target_user_id)

        try:
            await self.repository.add_invite(project_id, target_user_id, current_user_id)
            await self.repository.commit()
        except IntegrityError:
            await self.repository.rollback()
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Invitation already exists",
            ) from None

        return {"detail": "Invitation sent"}

    async def send_join_request(self, project_id: UUID, current_user_id: UUID):
        await self._get_project_or_404(project_id)

        current_user_role = await self.repository.get_user_role(project_id, current_user_id)
        if current_user_role:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Member already exists")

        await self._ensure_no_pending_invitation(project_id, current_user_id)

        try:
            request_id = await self.repository.add_request(project_id, current_user_id)
            await self.repository.commit()
        except IntegrityError:
            await self.repository.rollback()
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Invitation already exists",
            ) from None

        return {"request_id": request_id}

    async def accept_join_request(
        self,
        project_id: UUID,
        request_id: UUID,
        current_user_id: UUID,
    ):
        await self._require_invitation_manager(project_id, current_user_id)
        invitation = await self._get_pending_invitation(
            project_id,
            request_id,
            ProjectInviteType.REQUEST,
            "Request",
        )

        try:
            user_exists = await self.users_gateway.check_user_exists(invitation.user_id)
        except ExternalServiceUnavailable:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Auth service is unavailable for user verification",
            ) from None

        if not user_exists:
            invitation.status = RequestStatus.REJECTED
            await self.repository.commit()
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="The user who made this request no longer exists",
            )

        existing_staff = await self.repository.get_user_role(project_id, invitation.user_id)
        if existing_staff:
            invitation.status = RequestStatus.ACCEPTED
            await self.repository.commit()
            return {"detail": "User is already in staff"}

        await self._add_member_from_invitation(invitation)
        return {"detail": "User joined the project"}

    async def accept_invite_to_join(self, project_id: UUID, invite_id: UUID, current_user_id: UUID):
        invite = await self._get_pending_invitation(
            project_id,
            invite_id,
            ProjectInviteType.INVITE,
            "Invitation",
        )

        if invite.user_id != current_user_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You cannot accept an invitation addressed to someone else",
            )

        existing_staff = await self.repository.get_user_role(project_id, current_user_id)
        if existing_staff:
            invite.status = RequestStatus.ACCEPTED
            await self.repository.commit()
            return {"detail": "You are already in staff"}

        await self._add_member_from_invitation(invite)
        return {"detail": "You have successfully joined the project"}

    async def reject_invite_to_join(self, project_id: UUID, invite_id: UUID, current_user_id: UUID):
        invite = await self._get_pending_invitation(
            project_id,
            invite_id,
            ProjectInviteType.INVITE,
            "Invitation",
        )
        if invite.user_id != current_user_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You can only reject your own invites",
            )

        invite.status = RequestStatus.REJECTED
        await self.repository.commit()
        return {"detail": "Invite rejected successfully"}

    async def reject_join_request(self, project_id: UUID, request_id: UUID, current_user_id: UUID):
        await self._require_invitation_manager(project_id, current_user_id)
        join_request = await self._get_pending_invitation(
            project_id,
            request_id,
            ProjectInviteType.REQUEST,
            "Join request",
        )

        join_request.status = RequestStatus.REJECTED
        await self.repository.commit()
        return {"detail": "Join request rejected"}

    async def get_user_invites(self, user_id: UUID) -> list[ProjectInvitationSchema]:
        invitations = await self.repository.get_invitations_by_user_id(
            user_id,
            ProjectInviteType.INVITE,
        )
        return [ProjectInvitationSchema.model_validate(item) for item in invitations]

    async def get_user_requests(self, user_id: UUID) -> list[ProjectInvitationSchema]:
        invitations = await self.repository.get_invitations_by_user_id(
            user_id,
            ProjectInviteType.REQUEST,
        )
        return [ProjectInvitationSchema.model_validate(item) for item in invitations]

    async def _get_project_or_404(self, project_id: UUID):
        project = await self.repository.get_by_id(project_id)
        if not project:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")
        return project

    async def _ensure_user_exists(self, user_id: UUID) -> None:
        try:
            exists = await self.users_gateway.check_user_exists(user_id)
        except ExternalServiceUnavailable:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Auth service is unavailable for user verification",
            ) from None
        if not exists:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    async def _ensure_no_pending_invitation(self, project_id: UUID, user_id: UUID) -> None:
        exists = await self.repository.exists_invite_or_request(
            project_id,
            user_id,
            status=RequestStatus.PENDING,
        )
        if exists:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Invitation already exists",
            )

    async def _require_invitation_manager(self, project_id: UUID, user_id: UUID) -> StaffRole:
        await self._get_project_or_404(project_id)
        role = await self.repository.get_user_role(project_id, user_id)
        if not role or role == StaffRole.PARTICIPANT:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You have no rights to manage requests to this project",
            )
        return role

    async def _get_pending_invitation(
        self,
        project_id: UUID,
        invitation_id: UUID,
        invitation_type: ProjectInviteType,
        resource_name: str,
    ) -> ProjectInvitation:
        invitation = await self.repository.get_invitation_by_id(invitation_id)
        if not invitation or invitation.type != invitation_type:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"{resource_name} not found",
            )
        if invitation.project_id != project_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"{resource_name} does not belong to this project",
            )
        if invitation.status != RequestStatus.PENDING:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"{resource_name} is already processed",
            )
        return invitation

    async def _add_member_from_invitation(self, invitation: ProjectInvitation) -> None:
        try:
            await self.repository.add_to_staff(
                project_id=invitation.project_id,
                user_id=invitation.user_id,
                role=StaffRole.PARTICIPANT,
            )
            invitation.status = RequestStatus.ACCEPTED
            await self.repository.commit()
        except IntegrityError:
            await self.repository.rollback()
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="User is already in staff",
            ) from None
