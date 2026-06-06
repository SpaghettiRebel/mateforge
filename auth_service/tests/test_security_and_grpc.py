from datetime import UTC, datetime, timedelta
from uuid import uuid4

import grpc
import pytest
from fastapi import HTTPException
from jose import jwt

from auth_service.src.application.user_service import AccessType
from auth_service.src.infrastructure.config import settings
from auth_service.src.infrastructure.email import send_verification_email
from auth_service.src.infrastructure.exceptions import TokenExpiredError, TokenInvalidError
from auth_service.src.infrastructure.generated import users_pb2
from auth_service.src.infrastructure.security import create_token, decode_access_token
from auth_service.src.presentation.dependencies import get_current_user
from auth_service.src.presentation.grpc_handler import UsersServicer
from auth_service.src.presentation.schemas import UserData


def _token(user_id, *, token_type="auth", expires_delta=timedelta(minutes=5), sub=None):
    now = datetime.now(UTC)
    payload = {
        "sub": str(user_id) if sub is None else sub,
        "type": token_type,
        "iss": settings.JWT_ISSUER,
        "aud": settings.JWT_AUDIENCE,
        "iat": now,
        "nbf": now,
        "exp": now + expires_delta,
    }
    return jwt.encode(payload, settings.JWT_SECRET, algorithm=settings.JWT_ALGORITHM)


class AbortError(Exception):
    pass


class FakeGrpcContext:
    def __init__(self, token: str):
        self.token = token
        self.abort_code = None
        self.abort_details = None

    def invocation_metadata(self):
        return (("x-service-token", self.token),)

    async def abort(self, code, details):
        self.abort_code = code
        self.abort_details = details
        raise AbortError(details)


@pytest.mark.asyncio
async def test_auth_security_tokens_reject_bad_shape_and_wrong_type():
    user_id = uuid4()

    assert decode_access_token(create_token(user_id, "auth"), "auth") == user_id

    with pytest.raises(ValueError):
        create_token(user_id, "refresh")

    with pytest.raises(TokenInvalidError):
        decode_access_token(_token(user_id, token_type="verification"), "auth")

    with pytest.raises(TokenInvalidError):
        decode_access_token(_token(user_id, sub="not-a-uuid"), "auth")

    with pytest.raises(TokenExpiredError):
        decode_access_token(_token(user_id, expires_delta=timedelta(seconds=-1)), "auth")


@pytest.mark.asyncio
async def test_get_current_user_maps_token_errors_to_http_responses():
    user_id = uuid4()

    class UserServiceStub:
        async def get_user(self, requested_user_id, access_type=AccessType.FREE):
            assert requested_user_id == user_id
            assert access_type == AccessType.PRIVATE
            return UserData(
                id=user_id,
                email="current@test.com",
                username="current",
                bio=None,
                followers_count=0,
                following_count=0,
                created_at=datetime.now(UTC),
            )

    with pytest.raises(HTTPException) as missing:
        await get_current_user(None, UserServiceStub())
    assert missing.value.status_code == 403

    with pytest.raises(HTTPException) as invalid:
        await get_current_user("not-a-token", UserServiceStub())
    assert invalid.value.status_code == 401

    with pytest.raises(HTTPException) as expired:
        await get_current_user(_token(user_id, expires_delta=timedelta(seconds=-1)), UserServiceStub())
    assert expired.value.status_code == 401

    current = await get_current_user(_token(user_id), UserServiceStub())
    assert current.id == user_id
    assert current.email == "current@test.com"


@pytest.mark.asyncio
async def test_verification_email_uses_public_app_url(monkeypatch):
    sent_messages = []

    class FastMailStub:
        async def send_message(self, message):
            sent_messages.append(message)

    monkeypatch.setattr("auth_service.src.infrastructure.email.fastmail", FastMailStub())

    await send_verification_email("target@test.com", "verify-token")

    assert len(sent_messages) == 1
    assert sent_messages[0].recipients[0].email == "target@test.com"
    assert "http://testserver/auth/verify?token=verify-token" in sent_messages[0].body


@pytest.mark.asyncio
async def test_users_grpc_servicer_requires_service_token_and_valid_uuid():
    servicer = UsersServicer()
    request = users_pb2.UserRequest(user_id=str(uuid4()))

    wrong_token_context = FakeGrpcContext("wrong")
    with pytest.raises(AbortError):
        await servicer.GetUserExistence(request, wrong_token_context)
    assert wrong_token_context.abort_code == grpc.StatusCode.UNAUTHENTICATED

    invalid_uuid_context = FakeGrpcContext(settings.GRPC_SERVICE_TOKEN)
    with pytest.raises(AbortError):
        await servicer.GetUserExistence(users_pb2.UserRequest(user_id="bad-uuid"), invalid_uuid_context)
    assert invalid_uuid_context.abort_code == grpc.StatusCode.INVALID_ARGUMENT


@pytest.mark.asyncio
async def test_users_grpc_servicer_returns_existence(monkeypatch, db_session, verified_user):
    _, user = verified_user

    class SessionContext:
        async def __aenter__(self):
            return db_session

        async def __aexit__(self, exc_type, exc, tb):
            return False

    monkeypatch.setattr("auth_service.src.presentation.grpc_handler.async_session_factory", lambda: SessionContext())

    servicer = UsersServicer()

    existing = await servicer.GetUserExistence(
        users_pb2.UserRequest(user_id=str(user.id)),
        FakeGrpcContext(settings.GRPC_SERVICE_TOKEN),
    )
    missing = await servicer.GetUserExistence(
        users_pb2.UserRequest(user_id=str(uuid4())),
        FakeGrpcContext(settings.GRPC_SERVICE_TOKEN),
    )

    assert existing.exists is True
    assert missing.exists is False
