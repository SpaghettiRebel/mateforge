from uuid import UUID, uuid4
from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession
from auth_service.src.infrastructure.models import UserDB
from auth_service.src.presentation.schemas import UserCreate


class UserRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    @staticmethod
    def create_instance(user_data: UserCreate, hashed_password, is_verified):
        return UserDB(id=uuid4(),
                      email=user_data.email,
                      username=user_data.username,
                      hashed_password=hashed_password,
                      is_verified=is_verified)

    async def get_by_id(self, user_id: UUID) -> UserDB | None:
        return await self.session.get(UserDB, user_id)

    async def get_by_email(self, email: str) -> UserDB | None:
        query = select(UserDB).where(UserDB.email == email)
        result = await self.session.execute(query)
        return result.scalar_one_or_none()

    async def get_by_username(self, username: str) -> UserDB | None:
        query = select(UserDB).where(UserDB.username == username)
        result = await self.session.execute(query)
        return result.scalar_one_or_none()

    async def add(self, user: UserDB) -> UserDB:
        self.session.add(user)
        await self.session.flush()
        return user

    async def delete(self, user_id: UUID) -> None:
        query = delete(UserDB).where(UserDB.id == user_id)
        await self.session.execute(query)
        await self.session.commit()

    async def mark_as_verified(self, user_id: UUID) -> UserDB | None:
        user = await self.session.get(UserDB, user_id)
        if not user:
            return None

        user.is_verified = True
        await self.session.commit()
        return user

    async def update_bio(self, user_id: UUID, bio: str) -> UserDB | None:
        user = await self.session.get(UserDB, user_id)
        if not user:
            return None

        user.bio = bio
        await self.session.commit()
        return user
