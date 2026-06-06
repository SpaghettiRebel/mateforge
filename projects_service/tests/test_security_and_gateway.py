from datetime import UTC, datetime, timedelta
from types import SimpleNamespace

import grpc
import pytest
from fastapi import HTTPException
from jose import jwt

from projects_service.src.infrastructure.config import settings
from projects_service.src.infrastructure.exceptions import (
    ExternalServiceUnavailable,
    TokenExpiredError,
    TokenInvalidError,
)
from projects_service.src.infrastructure.grpc_client import UsersGrpcClient
from projects_service.src.infrastructure.security import decode_access_token
from projects_service.src.presentation.dependencies import (
    get_current_user_id,
    get_optional_user_id,
    get_users_gateway,
)


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


@pytest.mark.asyncio
async def test_access_token_dependencies_validate_missing_expired_and_wrong_type(user_id):
    token = _token(user_id)
    assert decode_access_token(token, "auth") == user_id
    assert await get_current_user_id(token) == user_id
    assert await get_optional_user_id(None) is None

    with pytest.raises(HTTPException) as missing:
        await get_current_user_id(None)
    assert missing.value.status_code == 401

    with pytest.raises(TokenInvalidError):
        decode_access_token(_token(user_id, token_type="refresh"), "auth")

    with pytest.raises(TokenInvalidError):
        decode_access_token(_token(user_id, sub="not-a-uuid"), "auth")

    with pytest.raises(TokenExpiredError):
        decode_access_token(_token(user_id, expires_delta=timedelta(seconds=-1)), "auth")

    with pytest.raises(HTTPException) as invalid_for_dependency:
        await get_current_user_id("not-a-token")
    assert invalid_for_dependency.value.status_code == 401


def test_users_gateway_dependency_requires_configured_app_state():
    gateway = object()
    request_with_gateway = SimpleNamespace(app=SimpleNamespace(state=SimpleNamespace(users_gateway=gateway)))
    request_without_gateway = SimpleNamespace(app=SimpleNamespace(state=SimpleNamespace()))

    assert get_users_gateway(request_with_gateway) is gateway

    with pytest.raises(HTTPException) as missing_gateway:
        get_users_gateway(request_without_gateway)
    assert missing_gateway.value.status_code == 503


@pytest.mark.asyncio
async def test_users_grpc_client_sends_service_token_metadata(user_id):
    class Stub:
        def __init__(self):
            self.request = None
            self.timeout = None
            self.metadata = None

        async def GetUserExistence(self, request, timeout, metadata):
            self.request = request
            self.timeout = timeout
            self.metadata = metadata
            return SimpleNamespace(exists=True)

    stub = Stub()
    client = UsersGrpcClient("auth", 50051, "service-token", 1.5)
    client._stub = stub

    assert await client.check_user_exists(user_id) is True
    assert stub.request.user_id == str(user_id)
    assert stub.timeout == 1.5
    assert stub.metadata == (("x-service-token", "service-token"),)


@pytest.mark.asyncio
async def test_users_grpc_client_wraps_rpc_errors(user_id):
    class FakeRpcError(grpc.aio.AioRpcError):
        def code(self):
            return grpc.StatusCode.UNAVAILABLE

    class Stub:
        async def GetUserExistence(self, request, timeout, metadata):
            raise FakeRpcError(grpc.StatusCode.UNAVAILABLE, None, None)

    client = UsersGrpcClient("auth", 50051, "service-token", 1.5)
    client._stub = Stub()

    with pytest.raises(ExternalServiceUnavailable):
        await client.check_user_exists(user_id)
