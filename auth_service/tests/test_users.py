import pytest

@pytest.mark.asyncio
async def test_user_social_logic(client, verified_user, db_session):
    user1_data, user1_id = verified_user

    # Создаем второго пользователя
    user2_payload = {"email": "user2@test.com", "username": "user2", "password": "Strong_password-33"}
    await client.post("/auth/register", json=user2_payload)

    from sqlalchemy import select, update
    from auth_service.src.infrastructure.models import UserDB
    user2 = (await db_session.execute(select(UserDB).where(UserDB.email == "user2@test.com"))).scalar_one()
    user2.is_verified = True
    await db_session.commit()
    user2_id = user2.id

    # Логинимся первым юзером
    login_resp = await client.post("/auth/login",
                                   data={"username": user1_data["email"], "password": user1_data["password"]})
    token = login_resp.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # 1. Получаем свой профиль (/me)
    me_resp = await client.get("/users/me", headers=headers)
    assert me_resp.status_code == 200
    assert me_resp.json()["email"] == user1_data["email"]

    # 2. Редактируем био
    edit_resp = await client.patch("/users/me", json={"bio": "I am a dev"}, headers=headers)
    assert edit_resp.status_code == 200
    assert edit_resp.json()["bio"] == "I am a dev"

    # 3. Подписка (Follow)
    follow_resp = await client.post(f"/users/{user2_id}/follow", headers=headers)
    assert follow_resp.status_code == 200

    # 4. Проверка счетчиков
    user2_resp = await client.get(f"/users/{user2_id}")
    assert user2_resp.json()["followers_count"] == 1

    # 5. Удаление аккаунта
    del_resp = await client.delete("/users/me", headers=headers)
    assert del_resp.status_code == 200

    # Проверка, что юзер исчез из БД
    check_user = await db_session.execute(select(UserDB).where(UserDB.id == user1_id))
    assert check_user.scalar_one_or_none() is None