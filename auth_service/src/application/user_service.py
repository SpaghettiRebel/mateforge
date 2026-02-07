from auth_service.src.presentation.schemas import UserRead, UserData
from auth_service.src.infrastructure.repositories.user_repository import UserRepository
from auth_service.src.infrastructure.repositories.token_repository import TokenRepository
from uuid import UUID
from fastapi import HTTPException, BackgroundTasks, status, Depends


class UserService:
    def __init__(
            self,
            user_repository: UserRepository,
            token_repository: TokenRepository
    ):
        self.user_repository = user_repository
        self.token_repository = token_repository

    async def get_user(self, user_id: UUID, access_type: str = 'free') -> UserRead | UserData:
        user = await self.user_repository.get_by_id(user_id)
        if not user:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                                detail="User not found")

        if access_type == 'private':
            return UserData.model_validate(user)

        return UserRead.model_validate(user)

    async def delete_user(self, user_id: UUID) -> dict:
        await self.token_repository.delete_all_user_tokens(str(user_id))
        await self.user_repository.delete(user_id)

        return {"msg": "Account deleted"}

    async def edit_user(self, user_id: UUID, bio: str) -> UserData:
        user = await self.user_repository.update_bio(user_id, bio)
        if not user:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                                detail="User not found")

        return user
