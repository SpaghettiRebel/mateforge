from datetime import datetime, timedelta, timezone
from uuid import UUID, uuid4

from jose import jwt
from passlib.context import CryptContext

from auth_service.src.infrastructure.config import settings
from auth_service.src.infrastructure.exceptions import TokenExpiredError, TokenInvalidError

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto", bcrypt__ident="2b")


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)


def create_token(user_id: UUID | str, token_type: str) -> str:
    now = datetime.now(timezone.utc)
    data = {
        'sub': str(user_id),
        'type': token_type,
        'iss': settings.JWT_ISSUER,
        'aud': settings.JWT_AUDIENCE,
        'iat': now,
        'nbf': now,
        'jti': str(uuid4()),
    }

    to_encode = data.copy()

    if token_type == 'verification':
        expire = now + timedelta(hours=settings.VERIFY_ACCESS_TOKEN_EXPIRE_HOURS)
    elif token_type == 'auth':
        expire = now + timedelta(minutes=settings.AUTH_ACCESS_TOKEN_EXPIRE_MINUTES)
    else:
        raise ValueError(f"Unsupported token type: {token_type}")

    to_encode.update({'exp': expire})
    encoded_jwt = jwt.encode(to_encode, settings.JWT_SECRET, algorithm=settings.JWT_ALGORITHM)

    return encoded_jwt


def decode_access_token(token: str, token_type: str) -> UUID:
    try:
        payload = jwt.decode(
            token,
            settings.JWT_SECRET,
            algorithms=[settings.JWT_ALGORITHM],
            audience=settings.JWT_AUDIENCE,
            issuer=settings.JWT_ISSUER,
        )
        if payload.get("type") != token_type:
            raise TokenInvalidError("Invalid token type")

        user_id = payload.get("sub")
        if not user_id:
            raise TokenInvalidError("Error with token structure (sub)")

        return UUID(user_id)
    except jwt.ExpiredSignatureError:
        raise TokenExpiredError("Token has expired") from None
    except (jwt.JWTError, ValueError):
        raise TokenInvalidError("Could not validate credentials") from None
