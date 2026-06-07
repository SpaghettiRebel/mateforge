from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy.exc import IntegrityError

from auth_service.src.infrastructure.repositories.skill_repository import SkillRepository
from auth_service.src.infrastructure.repositories.user_repository import UserRepository
from auth_service.src.presentation.schemas import (
    SkillCreate,
    SkillRead,
    UserSkillInput,
    UserSkillRead,
    UserSkillsReplace,
)


class SkillService:
    def __init__(
        self,
        skill_repository: SkillRepository,
        user_repository: UserRepository,
    ):
        self.skill_repository = skill_repository
        self.user_repository = user_repository

    async def create_skill(self, data: SkillCreate) -> SkillRead:
        skill = self.skill_repository.create_instance(data)
        try:
            await self.skill_repository.add(skill)
            await self.skill_repository.commit()
        except IntegrityError:
            await self.skill_repository.rollback()
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Skill name or slug already exists",
            ) from None
        return SkillRead.model_validate(skill)

    async def list_skills(
        self,
        *,
        search: str | None,
        group: str | None,
        page: int,
        limit: int,
    ) -> list[SkillRead]:
        skills = await self.skill_repository.list_skills(
            search=search,
            group=group,
            limit=limit,
            offset=(page - 1) * limit,
        )
        return [SkillRead.model_validate(skill) for skill in skills]

    async def get_user_skills(self, user_id: UUID) -> list[UserSkillRead]:
        await self._ensure_user_exists(user_id)
        return await self._read_user_skills(user_id)

    async def add_user_skill(self, user_id: UUID, data: UserSkillInput) -> list[UserSkillRead]:
        await self._ensure_user_exists(user_id)
        await self._ensure_skill_exists(data.skill_id)
        try:
            await self.skill_repository.add_user_skill(user_id, data)
            await self.skill_repository.commit()
        except IntegrityError:
            await self.skill_repository.rollback()
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Skill is already attached to this user",
            ) from None
        return await self._read_user_skills(user_id)

    async def replace_user_skills(
        self,
        user_id: UUID,
        data: UserSkillsReplace,
    ) -> list[UserSkillRead]:
        await self._ensure_user_exists(user_id)
        requested_ids = {item.skill_id for item in data.skills}
        existing = await self.skill_repository.get_by_ids(requested_ids)
        existing_ids = {skill.id for skill in existing}
        missing_ids = sorted(str(skill_id) for skill_id in requested_ids - existing_ids)
        if missing_ids:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={"message": "Skills not found", "skill_ids": missing_ids},
            )

        await self.skill_repository.replace_user_skills(user_id, data.skills)
        await self.skill_repository.commit()
        return await self._read_user_skills(user_id)

    async def update_user_skill(
        self,
        user_id: UUID,
        skill_id: UUID,
        level: int,
    ) -> list[UserSkillRead]:
        updated = await self.skill_repository.update_user_skill_level(user_id, skill_id, level)
        if not updated:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User skill not found",
            )
        await self.skill_repository.commit()
        return await self._read_user_skills(user_id)

    async def delete_user_skill(self, user_id: UUID, skill_id: UUID) -> None:
        deleted = await self.skill_repository.delete_user_skill(user_id, skill_id)
        if not deleted:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User skill not found",
            )
        await self.skill_repository.commit()

    async def _ensure_user_exists(self, user_id: UUID) -> None:
        if not await self.user_repository.exists(user_id):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found",
            )

    async def _ensure_skill_exists(self, skill_id: UUID) -> None:
        if await self.skill_repository.get_by_id(skill_id) is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Skill not found",
            )

    async def _read_user_skills(self, user_id: UUID) -> list[UserSkillRead]:
        links = await self.skill_repository.get_user_skills(user_id)
        return [UserSkillRead.model_validate(link) for link in links]
