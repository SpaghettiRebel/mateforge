from typing import List
from fastapi import APIRouter, Depends, Body
from uuid import UUID

from auth_service.src.presentation.schemas import UserRead, UserData
from auth_service.src.application.user_service import UserService
from auth_service.src.presentation.dependencies import get_service, get_current_user

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
        bio: str = Body(embed=True),
        current_user: UserData = Depends(get_current_user),
        user_service: UserService = Depends(get_service('user')),
):
    return await user_service.edit_user(current_user.id, bio)


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
    page: int = 1,
    limit: int = 20,
    user_service: UserService = Depends(get_service('user'))
):
    return await user_service.get_followers(user_id, page, limit)

@router.get("/{user_id}/following", response_model=List[UserRead])
async def get_user_following(
    user_id: UUID,
    page: int = 1,
    limit: int = 20,
    user_service: UserService = Depends(get_service('user'))
):
    return await user_service.get_following(user_id, page, limit)
