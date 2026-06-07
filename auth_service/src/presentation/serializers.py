from typing import Any

from sqlalchemy import inspect
from sqlalchemy.exc import NoInspectionAvailable

from auth_service.src.presentation.schemas import UserData, UserRead, UserSkillRead


def to_user_read(user: Any) -> UserRead:
    return UserRead(
        id=user.id,
        username=user.username,
        bio=user.bio,
        followers_count=user.followers_count,
        following_count=user.following_count,
        skills=_loaded_user_skills(user),
    )


def to_user_data(user: Any) -> UserData:
    return UserData(
        id=user.id,
        email=user.email,
        username=user.username,
        bio=user.bio,
        followers_count=user.followers_count,
        following_count=user.following_count,
        skills=_loaded_user_skills(user),
        created_at=user.created_at,
    )


def _loaded_user_skills(user: Any) -> list[UserSkillRead]:
    if _is_unloaded(user, "skill_links"):
        return []

    links = []
    for link in getattr(user, "skill_links", []) or []:
        if _is_unloaded(link, "skill"):
            continue
        links.append(link)

    links.sort(key=lambda link: (link.skill.group, link.skill.name, str(link.skill.id)))
    return [UserSkillRead.model_validate(link) for link in links]


def _is_unloaded(obj: Any, attribute_name: str) -> bool:
    try:
        return attribute_name in inspect(obj).unloaded
    except NoInspectionAvailable:
        return False
