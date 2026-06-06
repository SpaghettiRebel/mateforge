import asyncio
import json

import pytest
from sqlalchemy import inspect, select

from auth_service.src.infrastructure.exceptions import TokenInvalidError
from auth_service.src.infrastructure.models import UserDB
from auth_service.src.infrastructure.repositories.token_repository import TokenRepository
from auth_service.src.infrastructure.security import create_token, decode_access_token
from auth_service.tests.helpers import login_user


@pytest.mark.asyncio
async def test_auth_migrations_create_expected_schema(db_session):
    def inspect_schema(connection):
        inspector = inspect(connection)
        return {
            "tables": set(inspector.get_table_names()),
            "subscriptions_checks": {
                item["name"] for item in inspector.get_check_constraints("subscriptions")
            },
        }

    connection = await db_session.connection()
    schema = await connection.run_sync(inspect_schema)

    assert {"users", "subscriptions", "skills", "user_skills", "alembic_version"} <= schema["tables"]
    assert "ck_subscriptions_not_self" in schema["subscriptions_checks"]


@pytest.mark.asyncio
async def test_register_normalizes_user_and_requires_unique_identity(client, db_session):
    payload = {
        "email": "MixedCase@Test.COM",
        "username": "mate_user",
        "password": "Strong_password-33",
    }
    response = await client.post("/auth/register", json=payload)
    assert response.status_code == 201
    assert response.json()["username"] == "mate_user"

    user = (await db_session.execute(select(UserDB).where(UserDB.username == "mate_user"))).scalar_one()
    assert user.email == "mixedcase@test.com"
    assert not user.is_verified

    duplicate = await client.post("/auth/register", json={**payload, "email": "mixedcase@test.com"})
    assert duplicate.status_code == 409


@pytest.mark.asyncio
async def test_register_rejects_weak_password_and_bad_username(client):
    weak_password = await client.post(
        "/auth/register",
        json={"email": "bad@test.com", "username": "valid_name", "password": "password"},
    )
    assert weak_password.status_code == 422

    bad_username = await client.post(
        "/auth/register",
        json={"email": "bad2@test.com", "username": "bad username", "password": "Strong_password-33"},
    )
    assert bad_username.status_code == 422


@pytest.mark.asyncio
async def test_login_requires_verified_email(client):
    await client.post(
        "/auth/register",
        json={"email": "verify@test.com", "username": "verify_user", "password": "Strong_password-33"},
    )

    response = await client.post(
        "/auth/login",
        data={"username": "verify@test.com", "password": "Strong_password-33"},
    )
    assert response.status_code == 401
    assert response.json()["detail"] == "Email not verified"


@pytest.mark.asyncio
async def test_refresh_rotation_rejects_replay_and_stores_only_token_hash(client, redis_client, verified_user):
    user_data, user = verified_user
    tokens = await login_user(client, user_data["email"], user_data["password"], fingerprint="laptop")

    repository = TokenRepository(redis_client)
    raw_refresh = tokens["refresh_token"]
    digest = repository._digest(raw_refresh)

    assert await redis_client.get(f"refresh_token:{raw_refresh}") is None
    assert json.loads(await redis_client.get(f"refresh_token:{digest}"))["user_id"] == str(user.id)

    refreshed = await client.post(
        "/auth/refresh",
        json={"refresh_token": raw_refresh},
        headers={"X-Client-Fingerprint": "laptop"},
    )
    assert refreshed.status_code == 200
    assert refreshed.json()["refresh_token"] != raw_refresh

    replay = await client.post(
        "/auth/refresh",
        json={"refresh_token": raw_refresh},
        headers={"X-Client-Fingerprint": "laptop"},
    )
    assert replay.status_code == 401


@pytest.mark.asyncio
async def test_refresh_rotation_is_single_use_under_parallel_requests(client, verified_user):
    user_data, _ = verified_user
    tokens = await login_user(client, user_data["email"], user_data["password"], fingerprint="desktop")

    async def refresh_once():
        return await client.post(
            "/auth/refresh",
            json={"refresh_token": tokens["refresh_token"]},
            headers={"X-Client-Fingerprint": "desktop"},
        )

    responses = await asyncio.gather(refresh_once(), refresh_once())
    statuses = sorted(response.status_code for response in responses)

    assert statuses == [200, 401]


@pytest.mark.asyncio
async def test_refresh_rejects_wrong_device_and_consumes_session(client, verified_user):
    user_data, _ = verified_user
    tokens = await login_user(client, user_data["email"], user_data["password"], fingerprint="phone")

    wrong_device = await client.post(
        "/auth/refresh",
        json={"refresh_token": tokens["refresh_token"]},
        headers={"X-Client-Fingerprint": "browser"},
    )
    assert wrong_device.status_code == 403

    owner_retry = await client.post(
        "/auth/refresh",
        json={"refresh_token": tokens["refresh_token"]},
        headers={"X-Client-Fingerprint": "phone"},
    )
    assert owner_retry.status_code == 401


@pytest.mark.asyncio
async def test_logout_requires_body_token_and_revokes_only_owner_session(client, verified_user):
    user_data, _ = verified_user
    tokens = await login_user(client, user_data["email"], user_data["password"], fingerprint="desktop")

    query_logout = await client.delete(
        "/auth/logout",
        params={"refresh_token": tokens["refresh_token"]},
        headers={"Authorization": f"Bearer {tokens['access_token']}"},
    )
    assert query_logout.status_code == 422

    logout = await client.request(
        "DELETE",
        "/auth/logout",
        json={"refresh_token": tokens["refresh_token"]},
        headers={"Authorization": f"Bearer {tokens['access_token']}"},
    )
    assert logout.status_code == 200

    refresh = await client.post(
        "/auth/refresh",
        json={"refresh_token": tokens["refresh_token"]},
        headers={"X-Client-Fingerprint": "desktop"},
    )
    assert refresh.status_code == 401


@pytest.mark.asyncio
async def test_logout_all_revokes_every_refresh_session(client, verified_user):
    user_data, _ = verified_user
    phone = await login_user(client, user_data["email"], user_data["password"], fingerprint="phone")
    desktop = await login_user(client, user_data["email"], user_data["password"], fingerprint="desktop")

    response = await client.delete(
        "/auth/logout-all",
        headers={"Authorization": f"Bearer {phone['access_token']}"},
    )
    assert response.status_code == 200

    for tokens, fingerprint in [(phone, "phone"), (desktop, "desktop")]:
        refresh = await client.post(
            "/auth/refresh",
            json={"refresh_token": tokens["refresh_token"]},
            headers={"X-Client-Fingerprint": fingerprint},
        )
        assert refresh.status_code == 401


@pytest.mark.asyncio
async def test_rate_limiter_returns_429_on_fifth_failed_login(client):
    for attempt in range(1, 6):
        response = await client.post(
            "/auth/login",
            data={"username": "missing@test.com", "password": "Strong_password-33"},
        )
        expected_status = 429 if attempt == 5 else 401
        assert response.status_code == expected_status


@pytest.mark.asyncio
async def test_access_token_rejects_wrong_token_type():
    verification_token = create_token("00000000-0000-0000-0000-000000000001", "verification")
    with pytest.raises(TokenInvalidError):
        decode_access_token(verification_token, token_type="auth")
