from uuid import UUID

from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from auth_service.src.infrastructure.models import Skill, UserSkill
from auth_service.src.presentation.schemas import SkillCreate, UserSkillInput


class SkillRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    @staticmethod
    def create_instance(data: SkillCreate) -> Skill:
        return Skill(name=data.name, slug=data.slug, group=data.group)

    async def add(self, skill: Skill) -> Skill:
        self.session.add(skill)
        await self.session.flush()
        return skill

    async def get_by_id(self, skill_id: UUID) -> Skill | None:
        return await self.session.get(Skill, skill_id)

    async def get_by_ids(self, skill_ids: set[UUID]) -> list[Skill]:
        if not skill_ids:
            return []
        result = await self.session.execute(select(Skill).where(Skill.id.in_(skill_ids)))
        return list(result.scalars().all())

    async def list_skills(
        self,
        *,
        search: str | None,
        group: str | None,
        limit: int,
        offset: int,
    ) -> list[Skill]:
        query = select(Skill)
        if search:
            pattern = f"%{search.strip().lower()}%"
            query = query.where(
                func.lower(Skill.name).like(pattern)
                | func.lower(Skill.slug).like(pattern)
            )
        if group:
            query = query.where(Skill.group == group.strip().lower())

        query = query.order_by(Skill.group, Skill.name, Skill.id).limit(limit).offset(offset)
        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def get_user_skills(self, user_id: UUID) -> list[UserSkill]:
        query = (
            select(UserSkill)
            .options(selectinload(UserSkill.skill))
            .where(UserSkill.user_id == user_id)
            .join(UserSkill.skill)
            .order_by(Skill.group, Skill.name, Skill.id)
        )
        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def add_user_skill(self, user_id: UUID, data: UserSkillInput) -> None:
        self.session.add(
            UserSkill(
                user_id=user_id,
                skill_id=data.skill_id,
                level=data.level.value,
            )
        )
        await self.session.flush()

    async def replace_user_skills(self, user_id: UUID, skills: list[UserSkillInput]) -> None:
        await self.session.execute(delete(UserSkill).where(UserSkill.user_id == user_id))
        self.session.add_all(
            UserSkill(
                user_id=user_id,
                skill_id=item.skill_id,
                level=item.level.value,
            )
            for item in skills
        )
        await self.session.flush()

    async def update_user_skill_level(self, user_id: UUID, skill_id: UUID, level: int) -> bool:
        link = await self.session.get(
            UserSkill,
            {"user_id": user_id, "skill_id": skill_id},
        )
        if link is None:
            return False
        link.level = level
        await self.session.flush()
        return True

    async def delete_user_skill(self, user_id: UUID, skill_id: UUID) -> bool:
        result = await self.session.execute(
            delete(UserSkill).where(
                UserSkill.user_id == user_id,
                UserSkill.skill_id == skill_id,
            )
        )
        return bool(result.rowcount)

    async def commit(self) -> None:
        await self.session.commit()

    async def rollback(self) -> None:
        await self.session.rollback()
