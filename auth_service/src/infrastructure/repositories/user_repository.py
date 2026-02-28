from typing import List
from uuid import UUID, uuid4
from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession

from auth_service.src.infrastructure.models import UserDB, Subscription
from auth_service.src.presentation.schemas import UserCreate
from auth_service.src.infrastructure.exceptions import UserDoesNotExist


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

    async def get_by_id(self, user_id: UUID) -> UserDB:
        query = select(UserDB).where(UserDB.id == user_id)
        result = await self.session.execute(query)
        user = result.scalar_one_or_none()
        if not user:
            raise UserDoesNotExist

        return user

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

    async def mark_as_verified(self, user_id: UUID) -> None:
        user = await self.session.get(UserDB, user_id)
        if not user:
            raise UserDoesNotExist

        user.is_verified = True

    async def update_bio(self, user_id: UUID, bio: str) -> UserDB:
        user = await self.session.get(UserDB, user_id)
        if not user:
            raise UserDoesNotExist

        user.bio = bio

        await self.session.flush()

        query = select(UserDB).where(UserDB.id == user_id)
        result = await self.session.execute(query)
        return result.scalar_one()

    async def follow(self, user_id: UUID, follower_id: UUID) -> None:
        new_sub = Subscription(subscriber_id=follower_id, author_id=user_id)
        self.session.add(new_sub)

        await self.session.flush()


    async def get_followers(self, user_id: UUID, limit: int, offset: int) -> List[UserDB]:
        stmt = (
            select(UserDB)
            .join(Subscription, UserDB.id == Subscription.subscriber_id)
            .where(Subscription.author_id == user_id)
            .limit(limit)
            .offset(offset)
        )
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def get_following(self, user_id: UUID, limit: int, offset: int) -> List[UserDB]:
        stmt = (
            select(UserDB)
            .join(Subscription, UserDB.id == Subscription.author_id)
            .where(Subscription.subscriber_id == user_id)
            .limit(limit)
            .offset(offset)
        )
        result = await self.session.execute(stmt)
        return result.scalars().all()

