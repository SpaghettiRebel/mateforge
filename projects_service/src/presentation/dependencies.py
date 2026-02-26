from fastapi.security import OAuth2PasswordBearer
from fastapi import Depends, HTTPException, status

from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from projects_service.src.application.service import ProjectService
from projects_service.src.infrastructure.database import get_async_session
from projects_service.src.infrastructure.exceptions import TokenExpiredError, TokenInvalidError
from projects_service.src.infrastructure.repositories.project_repository import ProjectRepository
from projects_service.src.infrastructure.config import settings
from projects_service.src.infrastructure.security import decode_access_token

oauth2_scheme = OAuth2PasswordBearer(tokenUrl=f'http://{settings.USERS_SERVICE_URL}/auth/login')


def get_project_repository(session: AsyncSession = Depends(get_async_session)) -> ProjectRepository:
    return ProjectRepository(session)

async def get_current_user_id(token: str = Depends(oauth2_scheme)) -> UUID:
    try:
        return decode_access_token(token=token, token_type='auth')
    except TokenExpiredError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has expired",
        )
    except TokenInvalidError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
        )


def get_service(
        project_repository: ProjectRepository = Depends(get_project_repository),
):
    return ProjectService(project_repository)
