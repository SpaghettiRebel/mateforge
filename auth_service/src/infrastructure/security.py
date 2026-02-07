from passlib.context import CryptContext
from datetime import datetime, timedelta, timezone
from jose import jwt
from uuid import UUID

from auth_service.src.infrastructure.config import settings
from auth_service.src.infrastructure.exceptions import TokenExpiredError, TokenInvalidError

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto", bcrypt__ident="2b")


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)


def create_token(user_id: UUID, token_type: str) -> str:
    data = {
        'sub': str(user_id),
        'type': token_type,
    }

    to_encode = data.copy()

    if token_type == 'verification':
        expire = datetime.now(timezone.utc) + timedelta(hours=settings.VERIFY_ACCESS_TOKEN_EXPIRE_HOURS)
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=settings.AUTH_ACCESS_TOKEN_EXPIRE_MINUTES)

    to_encode.update({'exp': expire})
    encoded_jwt = jwt.encode(to_encode, settings.JWT_SECRET, algorithm=settings.JWT_ALGORITHM)

    return encoded_jwt


def decode_access_token(token: str, token_type: str) -> UUID | None:
    try:
        payload = jwt.decode(token, settings.JWT_SECRET, algorithms=[settings.JWT_ALGORITHM])
        if payload.get("type") != token_type:
            raise TokenInvalidError("Invalid token type")

        user_id = payload.get("sub")
        if not user_id:
            raise TokenInvalidError("Error with token structure (sub)")

        return UUID(user_id)
    except jwt.ExpiredSignatureError:
        raise TokenExpiredError("Token has expired")
    except (jwt.JWTError, ValueError):
        raise TokenInvalidError("Could not validate credentials")
