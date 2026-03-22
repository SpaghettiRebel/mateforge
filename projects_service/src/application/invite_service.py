from uuid import UUID
from fastapi import HTTPException, status

from projects_service.src.infrastructure.generated import users_pb2
from projects_service.src.infrastructure.models import StaffRole, RequestStatus, ProjectInviteType
from projects_service.src.infrastructure.repositories.project_repository import ProjectRepository

class InviteService:
    def __init__(self, project_repository: ProjectRepository):
        self.repository = project_repository

    async def send_invite(self, project_id: UUID, target_user_id: UUID, current_user_id: UUID):
        current_user_role = await self.repository.get_user_role(project_id, current_user_id)
        if not current_user_role or current_user_role == StaffRole.PARTICIPANT:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN,
                                detail="You have no rights to invite new members to this project")

        target_user_role = await self.repository.get_user_role(project_id, target_user_id)
        if target_user_role:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT,
                                detail="Member already exists")

        has_invited_or_requested = await self.repository.exists_invite_or_request(
            project_id,
            target_user_id,
            status=RequestStatus.PENDING
        )
        if has_invited_or_requested:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT,
                                detail="Invitation already exists")

        await self.repository.add_invite(project_id, target_user_id, current_user_id)
        await self.repository.session.commit()

    async def send_join_request(self, project_id: UUID, current_user_id: UUID):
        current_user_role = await self.repository.get_user_role(project_id, current_user_id)
        if current_user_role:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT,
                                detail="Member already exists")

        has_invited_or_requested = await self.repository.exists_invite_or_request(project_id,
                                                                                  current_user_id,
                                                                                  status=RequestStatus.PENDING)
        if has_invited_or_requested:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT,
                                detail="Invitation already exists")

        request_id = await self.repository.add_request(project_id, current_user_id)
        await self.repository.session.commit()

        return {'request_id': request_id}

    async def accept_join_request(
            self,
            project_id,
            request_id,
            current_user_id,
            grpc_client
    ):
        current_user_role = await self.repository.get_user_role(project_id, current_user_id)
        if not current_user_role or current_user_role == StaffRole.PARTICIPANT:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN,
                                detail="You have no rights to accept new members to this project")

        invitation = await self.repository.get_invitation_by_id(request_id)
        if not invitation or invitation.project_id != project_id:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Request not found")

        if invitation.status != RequestStatus.PENDING or invitation.type != ProjectInviteType.REQUEST:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Request is no longer pending")

        try:
            auth_response = await grpc_client.GetUserExistence(
                users_pb2.UserRequest(user_id=str(invitation.user_id))
            )

            if not auth_response.exists:
                invitation.status = RequestStatus.REJECTED
                await self.repository.session.commit()
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="The user who made this request no longer exists"
                )
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Auth service is unavailable for user verification"
            )

        existing_staff = await self.repository.get_user_role(project_id, invitation.user_id)
        if existing_staff:
            invitation.status = RequestStatus.ACCEPTED
            await self.repository.session.commit()
            return {"detail": "User is already in staff"}

        try:
            await self.repository.add_to_staff(
                project_id=project_id,
                user_id=invitation.user_id,
                role=StaffRole.PARTICIPANT
            )

            invitation.status = RequestStatus.ACCEPTED

            await self.repository.session.commit()
        except Exception as e:
            await self.repository.session.rollback()
            raise e

        return {"detail": "User joined the project"}

    async def accept_invite_to_join(self, project_id: UUID, invite_id: UUID, current_user_id: UUID):
        invite = await self.repository.get_invitation_by_id(invite_id)

        if not invite or invite.type != ProjectInviteType.INVITE:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Invitation not found"
            )

        if invite.project_id != project_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="This invitation does not belong to the specified project"
            )

        if invite.target_user_id != current_user_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You cannot accept an invitation addressed to someone else"
            )

        if invite.status != RequestStatus.PENDING:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid invitation status"
            )

        existing_staff = await self.repository.get_user_role(project_id, current_user_id)
        if existing_staff:
            invite.status = RequestStatus.ACCEPTED
            await self.repository.session.commit()
            return {"detail": "You are already in staff"}

        try:
            await self.repository.add_to_staff(
                project_id=project_id,
                user_id=current_user_id,
                role=StaffRole.PARTICIPANT
            )

            invite.status = RequestStatus.ACCEPTED

            await self.repository.session.commit()
        except Exception as e:
            await self.repository.session.rollback()
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to process the invitation. Please try again."
            )

        return {"detail": "You have successfully joined the project"}

    async def reject_invite_to_join(self, project_id: UUID, invite_id: UUID, current_user_id: UUID):
        invite = await self.repository.get_invitation_by_id(invite_id)

        if not invite or invite.type != ProjectInviteType.INVITE:
            raise HTTPException(status_code=404, detail="Invite not found")

        if invite.project_id != project_id:
            raise HTTPException(status_code=400, detail="Invite does not belong to this project")

        if invite.target_user_id != current_user_id:
            raise HTTPException(status_code=403, detail="You can only reject your own invites")

        if invite.status != RequestStatus.PENDING:
            raise HTTPException(status_code=400, detail=f"Cannot reject invite with status {invite.status}")

        try:
            invite.status = RequestStatus.REJECTED
            await self.repository.session.commit()
            return {"detail": "Invite rejected successfully"}
        except Exception as e:
            await self.repository.session.rollback()
            raise HTTPException(status_code=500, detail="Database error")

    async def reject_join_request(self, project_id: UUID, request_id: UUID, current_user_id: UUID):
        current_user_role = await self.repository.get_user_role(project_id, current_user_id)
        if not current_user_role or current_user_role == StaffRole.PARTICIPANT:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN,
                                detail="You have no rights to reject requests to this project")

        join_request = await self.repository.get_invitation_by_id(request_id)

        if not join_request or join_request.type != ProjectInviteType.REQUEST:
            raise HTTPException(status_code=404, detail="Join request not found")

        if join_request.project_id != project_id:
            raise HTTPException(status_code=400, detail="Request does not belong to this project")

        if join_request.status != RequestStatus.PENDING:
            raise HTTPException(status_code=400, detail="Request is already processed")

        try:
            join_request.status = RequestStatus.REJECTED
            await self.repository.session.commit()
        except Exception as e:
            await self.repository.session.rollback()
            raise HTTPException(status_code=500, detail="Internal server error")

        return {"detail": "Join request rejected"}
