from typing import List
from auth_service.src.presentation.schemas import UserRead, UserData
from auth_service.src.infrastructure.repositories.user_repository import UserRepository
from auth_service.src.infrastructure.repositories.token_repository import TokenRepository
from auth_service.src.infrastructure.exceptions import UserDoesNotExist
from sqlalchemy.exc import IntegrityError
from uuid import UUID
from fastapi import HTTPException, BackgroundTasks, status, Depends
from enum import Enum

class AccessType(Enum):
    FREE = 1
    PRIVATE = 2

class UserService:
    def __init__(
            self,
            user_repository: UserRepository,
            token_repository: TokenRepository
    ):
        self.user_repository = user_repository
        self.token_repository = token_repository

    async def get_user(self, user_id: UUID, access_type: Enum = AccessType.FREE) -> UserRead | UserData:
        try:
            user = await self.user_repository.get_by_id(user_id)
        except UserDoesNotExist:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                                detail="User not found")

        if access_type == AccessType.PRIVATE:
            return UserData.model_validate(user)

        return UserRead.model_validate(user)

    async def delete_user(self, user_id: UUID) -> dict:
        await self.token_repository.delete_all_user_tokens(str(user_id))
        await self.user_repository.delete(user_id)

        await self.user_repository.session.commit()

        return {"msg": "Account deleted"}

    async def edit_user(self, user_id: UUID, bio: str) -> UserData:
        try:
            user = await self.user_repository.update_bio(user_id, bio)

            await self.user_repository.session.commit()
            await self.user_repository.session.refresh(user)

            return UserData.model_validate(user)
        except UserDoesNotExist:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                                detail="User not found")

    async def follow_user(self, user_id: UUID, follower_id: UUID) -> dict:
        if user_id == follower_id:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                                detail="Cannot follow yourself")
        try:
            await self.user_repository.follow(user_id=user_id, follower_id=follower_id)
        except IntegrityError:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                                detail="Error due to follow")

        await self.user_repository.session.commit()

        return {"msg": "Subscribed successfully"}

    async def get_followers(self, user_id: UUID, page: int, limit: int) -> List[UserRead]:
        offset = (page - 1) * limit

        return await self.user_repository.get_followers(user_id, limit, offset)


    async def get_following(self, user_id: UUID, page: int, limit: int) -> List[UserRead]:
        offset = (page - 1) * limit

        return await self.user_repository.get_following(user_id, limit, offset)
