from fastapi import APIRouter, Depends, Body
from uuid import UUID

from auth_service.src.presentation.schemas import UserRead, UserData
from auth_service.src.application.user_service import UserService
from auth_service.src.presentation.dependencies import get_service, get_current_user

router = APIRouter()


@router.get("/me", response_model=UserData)
async def read_users_me(current_user: UserRead = Depends(get_current_user)):
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
