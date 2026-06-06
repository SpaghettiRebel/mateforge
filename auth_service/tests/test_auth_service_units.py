from uuid import uuid4

import pytest
from fastapi import BackgroundTasks, HTTPException
from sqlalchemy.exc import IntegrityError

from auth_service.src.application.login_service import AuthService
from auth_service.src.infrastructure.exceptions import UserDoesNotExist
from auth_service.src.presentation.schemas import UserCreate


class NoopTokenRepository:
    async def get_token_data(self, token):
        return None

    async def delete_all_user_tokens(self, user_id):
        return None


class NoopRateLimiter:
    async def check_limit(self, key, limit):
        return None

    async def increment(self, key, window_seconds):
        return 1, window_seconds


@pytest.mark.asyncio
async def test_register_rolls_back_on_database_race():
    class RacingUserRepository:
        rolled_back = False

        async def get_by_email(self, email):
            return None

        async def get_by_username(self, username):
            return None

        def create_instance(self, user_data, hashed_password, is_verified):
            return object()

        async def add(self, user):
            return None

        async def commit(self):
            raise IntegrityError("insert", {}, Exception("duplicate"))

        async def refresh(self, user):
            raise AssertionError("refresh should not run after failed commit")

        async def rollback(self):
            self.rolled_back = True

    repository = RacingUserRepository()
    service = AuthService(repository, NoopTokenRepository(), NoopRateLimiter())

    with pytest.raises(HTTPException) as conflict:
        await service.register_user(
            UserCreate(email="race@test.com", username="race_user", password="Strong_password-33"),
            BackgroundTasks(),
        )

    assert conflict.value.status_code == 409
    assert repository.rolled_back is True


@pytest.mark.asyncio
async def test_verify_user_maps_invalid_missing_and_success_cases():
    class UserRepository:
        def __init__(self):
            self.marked_user_id = None
            self.committed = False
            self.raise_missing = False

        async def mark_as_verified(self, user_id):
            if self.raise_missing:
                raise UserDoesNotExist
            self.marked_user_id = user_id

        async def commit(self):
            self.committed = True

    from auth_service.src.infrastructure.security import create_token

    repository = UserRepository()
    service = AuthService(repository, NoopTokenRepository(), NoopRateLimiter())
    user_id = uuid4()

    with pytest.raises(HTTPException) as invalid:
        await service.verify_user("not-a-token")
    assert invalid.value.status_code == 401

    repository.raise_missing = True
    with pytest.raises(HTTPException) as missing:
        await service.verify_user(create_token(user_id, "verification"))
    assert missing.value.status_code == 404

    repository.raise_missing = False
    result = await service.verify_user(create_token(user_id, "verification"))

    assert result == {"msg": "Email successfully verified"}
    assert repository.marked_user_id == user_id
    assert repository.committed is True


@pytest.mark.asyncio
async def test_logout_rejects_missing_and_foreign_refresh_tokens():
    class TokenRepository:
        def __init__(self, raw_data):
            self.raw_data = raw_data
            self.deleted = False

        async def get_token_data(self, refresh_token):
            return self.raw_data

        async def delete_token(self, user_id, refresh_token):
            self.deleted = True

    user_id = uuid4()

    missing_service = AuthService(object(), TokenRepository(None), NoopRateLimiter())
    with pytest.raises(HTTPException) as missing:
        await missing_service.logout("refresh", user_id)
    assert missing.value.status_code == 401

    foreign_service = AuthService(object(), TokenRepository(f'{{"user_id": "{uuid4()}"}}'), NoopRateLimiter())
    with pytest.raises(HTTPException) as foreign:
        await foreign_service.logout("refresh", user_id)
    assert foreign.value.status_code == 409
