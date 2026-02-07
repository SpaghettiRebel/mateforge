from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.ext.asyncio import AsyncSession
from redis.asyncio import Redis

from auth_service.src.presentation.schemas import UserData
from auth_service.src.infrastructure.security import decode_access_token
from auth_service.src.infrastructure.exceptions import TokenExpiredError, TokenInvalidError
from auth_service.src.infrastructure.database import get_async_session
from auth_service.src.infrastructure.redis import get_redis_client
from auth_service.src.infrastructure.repositories.user_repository import UserRepository
from auth_service.src.infrastructure.repositories.token_repository import TokenRepository
from auth_service.src.application.user_service import UserService
from auth_service.src.application.login_service import AuthService

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/login", auto_error=False)


def get_user_repository(session: AsyncSession = Depends(get_async_session)) -> UserRepository:
    return UserRepository(session)


async def get_token_repository(redis: Redis = Depends(get_redis_client)) -> TokenRepository:
    return TokenRepository(redis)


def get_service(service_type: str):

    async def service_dependency(
            user_repository: UserRepository = Depends(get_user_repository),
            token_repository: TokenRepository = Depends(get_token_repository)
    ):
        if service_type == 'user':
            return UserService(user_repository, token_repository)
        elif service_type == 'auth':
            return AuthService(user_repository, token_repository)
        else:
            raise ValueError(f"Unknown service type: {service_type}")

    return service_dependency


async def get_current_user(
        token: str | None = Depends(oauth2_scheme),
        user_service: UserService = Depends(get_service('user'))
) -> UserData:
    if not token:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Token expected",
            headers={"WWW-Authenticate": "Bearer"},
        )
    try:
        user_id = decode_access_token(token, token_type="auth")
    except TokenExpiredError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token expired",
            headers={"WWW-Authenticate": "Bearer"},
        )
    except (TokenInvalidError, ValueError):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user = await user_service.get_user(user_id, access_type='private')

    return UserData.model_validate(user)
