from jose import jwt
from uuid import UUID

from projects_service.src.infrastructure.config import settings
from projects_service.src.infrastructure.exceptions import TokenExpiredError, TokenInvalidError

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
