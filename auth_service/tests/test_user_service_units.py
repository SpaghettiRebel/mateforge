from datetime import UTC, datetime
from types import SimpleNamespace
from uuid import uuid4

import pytest
from fastapi import HTTPException
from sqlalchemy.exc import IntegrityError

from auth_service.src.application.user_service import AccessType, UserService
from auth_service.src.infrastructure.exceptions import UserDoesNotExist


class TokenRepositoryStub:
    def __init__(self):
        self.deleted_user_id = None

    async def delete_all_user_tokens(self, user_id):
        self.deleted_user_id = user_id


class UserRepositoryStub:
    def __init__(self, user):
        self.user = user
        self.deleted_user_id = None
        self.commits = 0
        self.rolled_back = False
        self.raise_missing = False
        self.raise_integrity = False
        self.follow_args = None
        self.followers_args = None
        self.following_args = None

    async def get_by_id(self, user_id):
        if self.raise_missing:
            raise UserDoesNotExist
        return self.user

    async def delete(self, user_id):
        self.deleted_user_id = user_id

    async def commit(self):
        self.commits += 1

    async def refresh(self, user):
        return None

    async def update_bio(self, user_id, bio):
        if self.raise_missing:
            raise UserDoesNotExist
        self.user.bio = bio
        return self.user

    async def follow(self, user_id, follower_id):
        if self.raise_integrity:
            raise IntegrityError("insert", {}, Exception("duplicate"))
        self.follow_args = (user_id, follower_id)

    async def rollback(self):
        self.rolled_back = True

    async def get_followers(self, user_id, limit, offset):
        self.followers_args = (user_id, limit, offset)
        return [self.user]

    async def get_following(self, user_id, limit, offset):
        self.following_args = (user_id, limit, offset)
        return [self.user]


def _user(user_id):
    return SimpleNamespace(
        id=user_id,
        email="unit@test.com",
        username="unit",
        bio=None,
        followers_count=0,
        following_count=0,
        created_at=datetime.now(UTC),
    )


@pytest.mark.asyncio
async def test_user_service_get_edit_delete_and_pagination_paths():
    user_id = uuid4()
    user = _user(user_id)
    user_repository = UserRepositoryStub(user)
    token_repository = TokenRepositoryStub()
    service = UserService(user_repository, token_repository)

    public_user = await service.get_user(user_id)
    private_user = await service.get_user(user_id, access_type=AccessType.PRIVATE)
    edited = await service.edit_user(user_id, "Updated bio")
    followers = await service.get_followers(user_id, page=3, limit=10)
    following = await service.get_following(user_id, page=2, limit=5)
    deleted = await service.delete_user(user_id)

    assert public_user.username == "unit"
    assert not hasattr(public_user, "email")
    assert private_user.email == "unit@test.com"
    assert edited.bio == "Updated bio"
    assert followers[0] is user
    assert following[0] is user
    assert user_repository.followers_args == (user_id, 10, 20)
    assert user_repository.following_args == (user_id, 5, 5)
    assert deleted == {"msg": "Account deleted"}
    assert token_repository.deleted_user_id == str(user_id)
    assert user_repository.deleted_user_id == user_id
    assert user_repository.commits == 2


@pytest.mark.asyncio
async def test_user_service_maps_missing_user_and_follow_errors():
    user_id = uuid4()
    follower_id = uuid4()
    user_repository = UserRepositoryStub(_user(user_id))
    service = UserService(user_repository, TokenRepositoryStub())

    user_repository.raise_missing = True
    with pytest.raises(HTTPException) as missing_get:
        await service.get_user(user_id)
    assert missing_get.value.status_code == 404

    with pytest.raises(HTTPException) as missing_edit:
        await service.edit_user(user_id, "Bio")
    assert missing_edit.value.status_code == 404

    user_repository.raise_missing = False
    with pytest.raises(HTTPException) as self_follow:
        await service.follow_user(user_id, user_id)
    assert self_follow.value.status_code == 400

    user_repository.raise_integrity = True
    with pytest.raises(HTTPException) as duplicate_follow:
        await service.follow_user(user_id, follower_id)

    assert duplicate_follow.value.status_code == 400
    assert user_repository.rolled_back is True
