import pytest
from sqlalchemy import select

from auth_service.src.infrastructure.models import UserDB
from auth_service.tests.helpers import login_user


@pytest.mark.asyncio
async def test_user_profile_edit_follow_pagination_and_delete(client, verified_user, db_session):
    user1_data, user1 = verified_user
    user1_id = user1.id
    user2_payload = {
        "email": "user2@test.com",
        "username": "user2",
        "password": "Strong_password-33",
    }
    await client.post("/auth/register", json=user2_payload)
    user2 = (await db_session.execute(select(UserDB).where(UserDB.email == "user2@test.com"))).scalar_one()
    user2.is_verified = True
    await db_session.commit()
    await db_session.refresh(user2)
    user2_id = user2.id

    tokens = await login_user(client, user1_data["email"], user1_data["password"])
    headers = {"Authorization": f"Bearer {tokens['access_token']}"}

    me = await client.get("/users/me", headers=headers)
    assert me.status_code == 200
    assert me.json()["email"] == user1_data["email"]

    edit = await client.patch("/users/me", json={"bio": "I build games"}, headers=headers)
    assert edit.status_code == 200
    assert edit.json()["bio"] == "I build games"

    self_follow = await client.post(f"/users/{user1_id}/follow", headers=headers)
    assert self_follow.status_code == 400

    follow = await client.post(f"/users/{user2_id}/follow", headers=headers)
    assert follow.status_code == 200

    invalid_pagination = await client.get(f"/users/{user2_id}/followers", params={"page": 0, "limit": 500})
    assert invalid_pagination.status_code == 422

    followers = await client.get(f"/users/{user2_id}/followers")
    assert followers.status_code == 200
    assert followers.json()[0]["id"] == str(user1_id)

    user2_public = await client.get(f"/users/{user2_id}")
    assert user2_public.json()["followers_count"] == 1

    delete = await client.delete("/users/me", headers=headers)
    assert delete.status_code == 200
    assert (await db_session.execute(select(UserDB).where(UserDB.id == user1_id))).scalar_one_or_none() is None


@pytest.mark.asyncio
async def test_duplicate_follow_is_rejected(client, verified_user, db_session):
    user1_data, _ = verified_user
    user2_payload = {
        "email": "duplicate-target@test.com",
        "username": "dup_target",
        "password": "Strong_password-33",
    }
    await client.post("/auth/register", json=user2_payload)
    user2 = (await db_session.execute(select(UserDB).where(UserDB.email == user2_payload["email"]))).scalar_one()
    user2_id = user2.id

    tokens = await login_user(client, user1_data["email"], user1_data["password"])
    headers = {"Authorization": f"Bearer {tokens['access_token']}"}

    first = await client.post(f"/users/{user2_id}/follow", headers=headers)
    duplicate = await client.post(f"/users/{user2_id}/follow", headers=headers)

    assert first.status_code == 200
    assert duplicate.status_code == 400


@pytest.mark.asyncio
async def test_private_fields_are_not_returned_from_public_profile(client, verified_user):
    _, user = verified_user
    response = await client.get(f"/users/{user.id}")
    assert response.status_code == 200
    assert "email" not in response.json()
