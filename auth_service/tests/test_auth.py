import pytest
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

    user.is_verified = True
    await db_session.commit()

    login_data = {
        "username": "real_postgres@test.com",
        "password": "Strong_password-33",
        "client_id": "browser_chrome_v2"
    }

    resp_login = await client.post("/auth/login", data=login_data)

    assert resp_login.status_code == 403
