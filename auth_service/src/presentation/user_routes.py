from typing import List
from uuid import UUID

from fastapi import APIRouter, Depends, Query

from auth_service.src.application.skill_service import SkillService
from auth_service.src.application.user_service import UserService
from auth_service.src.presentation.dependencies import get_current_user, get_service, get_skill_service
from auth_service.src.presentation.schemas import (
    UserBioUpdate,
    UserData,
    UserRead,
    UserSkillInput,
    UserSkillLevelUpdate,
    UserSkillRead,
    UserSkillsReplace,
)

router = APIRouter()


@router.get("/me", response_model=UserData)
async def read_users_me(current_user: UserData = Depends(get_current_user)):
    return current_user


@router.delete("/me")
async def delete_current_user_account(
    current_user: UserData = Depends(get_current_user),
    user_service: UserService = Depends(get_service('user'))
):
    return await user_service.delete_user(current_user.id)


@router.patch("/me", response_model=UserData)
async def edit_current_user(
    payload: UserBioUpdate,
    current_user: UserData = Depends(get_current_user),
    user_service: UserService = Depends(get_service('user')),
):
    return await user_service.edit_user(current_user.id, payload.bio)


@router.get("/me/skills", response_model=list[UserSkillRead])
async def get_current_user_skills(
    current_user: UserData = Depends(get_current_user),
    skill_service: SkillService = Depends(get_skill_service),
):
    return await skill_service.get_user_skills(current_user.id)


@router.post("/me/skills", response_model=list[UserSkillRead], status_code=201)
async def add_current_user_skill(
    payload: UserSkillInput,
    current_user: UserData = Depends(get_current_user),
    skill_service: SkillService = Depends(get_skill_service),
):
    return await skill_service.add_user_skill(current_user.id, payload)


@router.put("/me/skills", response_model=list[UserSkillRead])
async def replace_current_user_skills(
    payload: UserSkillsReplace,
    current_user: UserData = Depends(get_current_user),
    skill_service: SkillService = Depends(get_skill_service),
):
    return await skill_service.replace_user_skills(current_user.id, payload)


@router.patch("/me/skills/{skill_id}", response_model=list[UserSkillRead])
async def update_current_user_skill(
    skill_id: UUID,
    payload: UserSkillLevelUpdate,
    current_user: UserData = Depends(get_current_user),
    skill_service: SkillService = Depends(get_skill_service),
):
    return await skill_service.update_user_skill(current_user.id, skill_id, payload.level.value)


@router.delete("/me/skills/{skill_id}", status_code=204)
async def delete_current_user_skill(
    skill_id: UUID,
    current_user: UserData = Depends(get_current_user),
    skill_service: SkillService = Depends(get_skill_service),
):
    await skill_service.delete_user_skill(current_user.id, skill_id)


@router.get("/{user_id}/skills", response_model=list[UserSkillRead])
async def get_user_skills(
    user_id: UUID,
    skill_service: SkillService = Depends(get_skill_service),
):
    return await skill_service.get_user_skills(user_id)


@router.get("/{user_id}", response_model=UserRead)
async def get_user(
    user_id: UUID,
    user_service: UserService = Depends(get_service('user'))
):
    return await user_service.get_user(user_id)

@router.post("/{user_id}/follow")
async def follow_user(
    user_id: UUID,
    current_user: UserData = Depends(get_current_user),
    user_service: UserService = Depends(get_service('user'))
):
    return await user_service.follow_user(user_id=user_id, follower_id=current_user.id)

@router.get("/{user_id}/followers", response_model=List[UserRead])
async def get_user_followers(
    user_id: UUID,
    page: int = Query(default=1, ge=1),
    limit: int = Query(default=20, ge=1, le=100),
    user_service: UserService = Depends(get_service('user'))
):
    return await user_service.get_followers(user_id, page, limit)

@router.get("/{user_id}/following", response_model=List[UserRead])
async def get_user_following(
    user_id: UUID,
    page: int = Query(default=1, ge=1),
    limit: int = Query(default=20, ge=1, le=100),
    user_service: UserService = Depends(get_service('user'))
):
    return await user_service.get_following(user_id, page, limit)
