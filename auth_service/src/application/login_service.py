from auth_service.src.presentation.schemas import UserCreate, UserRead, Token
from auth_service.src.infrastructure.repositories.user_repository import UserRepository
from auth_service.src.infrastructure.repositories.token_repository import TokenRepository
from auth_service.src.infrastructure.repositories.rate_limiter import RateLimiter
from auth_service.src.infrastructure.security import hash_password, verify_password, create_token, decode_access_token
from auth_service.src.infrastructure.email import send_verification_email
from auth_service.src.infrastructure.config import settings
from auth_service.src.infrastructure.exceptions import TokenExpiredError, TokenInvalidError

from uuid import uuid4, UUID
import json
import logging
from fastapi import HTTPException, BackgroundTasks, status, Depends

logger = logging.getLogger(__name__)


class AuthService:
    def __init__(
            self,
            user_repository: UserRepository,
            token_repository: TokenRepository,
            rate_limiter: RateLimiter
    ):
        self.user_repository = user_repository
        self.token_repository = token_repository
        self.rate_limiter = rate_limiter

    async def register_user(self, user_data: UserCreate, background_tasks: BackgroundTasks) -> UserRead:

        is_exist_email = await self.user_repository.get_by_email(user_data.email)
        if is_exist_email:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT,
                                detail="Email already exists")

        is_exist_username = await self.user_repository.get_by_username(user_data.username)
        if is_exist_username:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT,
                                detail="Username already exists")

        hashed_password = hash_password(user_data.password)
        user = self.user_repository.create_instance(user_data=user_data,
                                                    hashed_password=hashed_password,
                                                    is_verified=False)

        await self.user_repository.add(user=user)
        await self.user_repository.session.commit()
        await self.user_repository.session.refresh(user)

        verification_token = create_token(user_id=user.id, token_type='verification')
        background_tasks.add_task(send_verification_email, user.email, verification_token)

        return UserRead.model_validate(user)

    async def authenticate_user(self, email: str, password: str, fingerprint: str | None) -> dict:
        limiter_key = f"login:{email}"
        await self.rate_limiter.check_limit(key=limiter_key, limit=5)

        user = await self.user_repository.get_by_email(email)
        if not user:
            await self.rate_limiter.increment(key=limiter_key, window_seconds=300)
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED,
                                detail="Invalid email or password")

        is_password_correct = verify_password(password, user.hashed_password)
        if not is_password_correct:
            await self.rate_limiter.increment(key=limiter_key, window_seconds=300)
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED,
                                detail="Invalid email or password")

        if not user.is_verified:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED,
                                detail="Email not verified")

        await self.rate_limiter.reset(key=limiter_key)

        access_token = create_token(user_id=user.id, token_type='auth')
        refresh_token = str(uuid4())

        session_data = json.dumps({
            "user_id": str(user.id),
            "fingerprint": fingerprint or "unknown"
        })
        ttl = settings.REFRESH_TOKEN_EXPIRE_DAYS * 24 * 60 * 60

        await self.token_repository.save_token(user.id, refresh_token, session_data, ttl)
        logger.info(f"Successfully saved refresh token for user {user.id}. TTL: {ttl}s")

        return {"access_token": access_token, "refresh_token": refresh_token, "token_type": "bearer"}

    async def refresh_session(self, refresh_token: str, fingerprint: str | None) -> Token:
        raw_data = await self.token_repository.get_token_data(refresh_token)

        if not raw_data:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED,
                                detail="Invalid or expired refresh token")

        data = json.loads(raw_data)

        stored_fingerprint = data.get('fingerprint')
        if stored_fingerprint != 'unknown' and stored_fingerprint != fingerprint:
            await self.token_repository.delete_token(refresh_token)
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN,
                                detail="Wrong device")

        await self.token_repository.delete_token(refresh_token)

        new_access_token = create_token(user_id=data['user_id'], token_type='auth')
        new_refresh_token = str(uuid4())

        data['fingerprint'] = fingerprint or "unknown"
        ttl = settings.REFRESH_TOKEN_EXPIRE_DAYS * 24 * 60 * 60

        await self.token_repository.save_token(new_refresh_token, json.dumps(data), ttl)
        logger.info(f"Successfully saved refresh token for user {data['user_id']}. TTL: {ttl}s")

        return Token(access_token=new_access_token, refresh_token=new_refresh_token, token_type="bearer")

    async def verify_user(self, token: str) -> dict:
        try:
            user_id = decode_access_token(token, token_type='verification')
        except TokenExpiredError:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token expired",
                headers={"WWW-Authenticate": "Bearer"},
            )
        except TokenInvalidError:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token",
            )

        user = await self.user_repository.mark_as_verified(user_id)
        if not user:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                                detail="User not found")

        return {"msg": "Email successfully verified"}

    async def logout(self, refresh_token: str, user_id: UUID) -> dict:
        raw_data = await self.token_repository.get_token_data(refresh_token)
        if not raw_data:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token",
            )

        data = json.loads(raw_data)
        stored_user_id = data.get("user_id")
        if stored_user_id != str(user_id):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Invalid token",
            )

        await self.token_repository.delete_token(user_id, refresh_token)
        return {"msg": "Logged out successfully"}

    async def logout_all_sessions(self, user_id: UUID) -> dict:
        await self.token_repository.delete_all_user_tokens(str(user_id))
        return {"msg": "Logged out from all devices"}
