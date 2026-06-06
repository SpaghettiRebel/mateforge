from uuid import UUID

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.ext.asyncio import AsyncSession

from projects_service.src.application.invite_service import InviteService
from projects_service.src.application.ports import UsersGateway
from projects_service.src.application.projects_managing_service import ProjectService
from projects_service.src.infrastructure.config import settings
from projects_service.src.infrastructure.database import get_async_session
from projects_service.src.infrastructure.exceptions import TokenExpiredError, TokenInvalidError
from projects_service.src.infrastructure.repositories.project_repository import ProjectRepository
from projects_service.src.infrastructure.security import decode_access_token

oauth2_scheme = OAuth2PasswordBearer(tokenUrl=settings.AUTH_LOGIN_URL, auto_error=False)


def get_project_repository(session: AsyncSession = Depends(get_async_session)) -> ProjectRepository:
    return ProjectRepository(session)

async def get_current_user_id(token: str | None = Depends(oauth2_scheme)) -> UUID:
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
        )

    try:
        return decode_access_token(token=token, token_type='auth')
    except TokenExpiredError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has expired",
        ) from None
    except TokenInvalidError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
        ) from None


async def get_optional_user_id(token: str | None = Depends(oauth2_scheme)) -> UUID | None:
    if not token:
        return None

    return await get_current_user_id(token)


def get_project_service(
        project_repository: ProjectRepository = Depends(get_project_repository),
):
    return ProjectService(project_repository)


def get_users_gateway(request: Request) -> UsersGateway:
    gateway = getattr(request.app.state, "users_gateway", None)
    if gateway is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Auth service gateway is not configured",
        )
    return gateway


def get_invite_service(
        project_repository: ProjectRepository = Depends(get_project_repository),
        users_gateway: UsersGateway = Depends(get_users_gateway),
):
    return InviteService(project_repository, users_gateway)
