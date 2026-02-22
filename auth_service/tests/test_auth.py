import pytest
import asyncio
from sqlalchemy import select
from auth_service.src.infrastructure.models import UserDB


@pytest.mark.asyncio
async def test_full_registration_flow_success(client, db_session):
    payload = {
        "email": "real_postgres@test.com",
        "username": "pg_master",
        "password": "Strong_password-33",
        "fingerprint": "browser_chrome_v1"
    }

    response = await client.post("/auth/register", json=payload)

    assert response.status_code == 201
    data = response.json()
    assert data["username"] == payload["username"]

    stmt = select(UserDB).where(UserDB.email == "real_postgres@test.com")
    result = await db_session.execute(stmt)
    user = result.scalar_one_or_none()

    assert user is not None
    assert user.username == "pg_master"
    assert user.is_verified == False

    user.is_verified = True
    await db_session.commit()

    login_data = {
        "username": "real_postgres@test.com",
        "password": "Strong_password-33",
        "client_id": "browser_chrome_v1"
    }

    resp_login = await client.post("/auth/login", data=login_data)

    assert resp_login.status_code == 200
    tokens = resp_login.json()
    assert "access_token" in tokens

@pytest.mark.asyncio
async def test_full_registration_flow_invalid_email(client, db_session):
    payload = {
        "email": "test_email",
        "username": "pg_master",
        "password": "Strong_password-33",
        "fingerprint": "browser_chrome_v1"
    }

    response = await client.post("/auth/register", json=payload)

    assert response.status_code == 422

@pytest.mark.asyncio
async def test_full_registration_flow_invalid_password(client, db_session):
    payload = {
        "email": "real_postgres@test.com",
        "username": "pg_master",
        "password": "password",
        "fingerprint": "browser_chrome_v1"
    }

    response = await client.post("/auth/register", json=payload)

    assert response.status_code == 422

@pytest.mark.asyncio
async def test_full_registration_flow_invalid_fingerprint(client, db_session):
    payload = {
        "email": "real_postgres@test.com",
        "username": "pg_master",
        "password": "Strong_password-33",
        "fingerprint": "browser_chrome_v1"
    }

    response = await client.post("/auth/register", json=payload)

    assert response.status_code == 201
    data = response.json()
    assert data["username"] == payload["username"]

    stmt = select(UserDB).where(UserDB.email == "real_postgres@test.com")
    result = await db_session.execute(stmt)
    user = result.scalar_one_or_none()

    assert user is not None
    assert user.username == "pg_master"
    assert user.is_verified == False


    login_data = {
        "username": "real_postgres@test.com",
        "password": "Strong_password-33",
        "client_id": "browser_chrome_v2"
    }

    resp_login = await client.post("/auth/login", data=login_data)

    assert resp_login.status_code == 401


@pytest.mark.asyncio
async def test_auth_happy_path(client, db_session):
    email = "happy@test.com"
    await client.post("/auth/register", json={"email": email, "username": "happy", "password": "Strong_password-33"})

    from sqlalchemy import update
    from auth_service.src.infrastructure.models import UserDB
    await db_session.execute(update(UserDB).where(UserDB.email == email).values(is_verified=True))
    await db_session.commit()

    login_data = {"username": email, "password": "Strong_password-33"}
    resp = await client.post("/auth/login", data=login_data, headers={"User-Agent": "iphone-15"})
    tokens = resp.json()

    refresh_resp = await client.post(
        "/auth/refresh",
        json={"refresh_token": tokens["refresh_token"]},
        headers={"User-Agent": "iphone-15"}
    )
    assert refresh_resp.status_code == 200
    new_tokens = refresh_resp.json()

    logout_resp = await client.delete(
        "/auth/logout",
        params={"refresh_token": new_tokens["refresh_token"]},
        headers={"Authorization": f"Bearer {new_tokens['access_token']}"}
    )
    assert logout_resp.status_code == 200


@pytest.mark.asyncio
async def test_auth_security_fingerprint_protection(client, db_session):
    email = "security@test.com"
    await client.post("/auth/register", json={"email": email, "username": "guard", "password": "Strong_password-33"})

    from sqlalchemy import update
    from auth_service.src.infrastructure.models import UserDB
    await db_session.execute(update(UserDB).where(UserDB.email == email).values(is_verified=True))
    await db_session.commit()

    resp = await client.post("/auth/login", data={"username": email, "password": "Strong_password-33"},
                             headers={"User-Agent": "user-device"})
    refresh_token = resp.json()["refresh_token"]

    hacker_resp = await client.post(
        "/auth/refresh",
        json={"refresh_token": refresh_token},
        headers={"User-Agent": "hacker-device"}
    )
    assert hacker_resp.status_code == 403
    assert hacker_resp.json()["detail"] == "Wrong device"

    owner_retry = await client.post(
        "/auth/refresh",
        json={"refresh_token": refresh_token},
        headers={"User-Agent": "user-device"}
    )
    assert owner_retry.status_code == 401


@pytest.mark.asyncio
async def test_auth_errors(client):
    bad_payload = {
        "email": "bad@test.com",
        "username": "baduser",
        "password": "123"
    }
    resp = await client.post("/auth/register", json=bad_payload)
    assert resp.status_code == 422

    login_data = {"username": "nonexistent@test.com", "password": "Password12345"}
    for _ in range(6):
        resp = await client.post("/auth/login", data=login_data)

    assert resp.status_code in [429, 401]


@pytest.mark.asyncio
async def test_logout_all_sessions_logic(client, db_session):
    email = "multidevice@test.com"
    await client.post("/auth/register", json={
        "email": email, "username": "multiman", "password": "Strong_password-33"
    })

    from sqlalchemy import update
    from auth_service.src.infrastructure.models import UserDB
    await db_session.execute(update(UserDB).where(UserDB.email == email).values(is_verified=True))
    await db_session.commit()

    resp1 = await client.post("/auth/login",
                              data={"username": email, "password": "Strong_password-33"},
                              headers={"User-Agent": "Mobile-App"})
    token_mobile = resp1.json()["refresh_token"]
    access_token_mobile = resp1.json()["access_token"]

    resp2 = await client.post("/auth/login",
                              data={"username": email, "password": "Strong_password-33"},
                              headers={"User-Agent": "Desktop-Browser"})
    token_desktop = resp2.json()["refresh_token"]

    for t, agent in [(token_mobile, "Mobile-App"), (token_desktop, "Desktop-Browser")]:
        check = await client.post("/auth/refresh", json={"refresh_token": t}, headers={"User-Agent": agent})
        assert check.status_code == 200

    logout_all_resp = await client.delete(
        "/auth/logout-all",
        headers={"Authorization": f"Bearer {access_token_mobile}"}
    )
    assert logout_all_resp.status_code == 200

    for t, agent in [(token_mobile, "Mobile-App"), (token_desktop, "Desktop-Browser")]:
        final_check = await client.post("/auth/refresh", json={"refresh_token": t}, headers={"User-Agent": agent})
        assert final_check.status_code == 401
        assert final_check.json()["detail"] == "Invalid or expired refresh token"
