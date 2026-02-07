from fastapi import APIRouter, Depends, BackgroundTasks, Header, Body
from fastapi.security import OAuth2PasswordRequestForm
from auth_service.src.presentation.schemas import UserCreate, UserRead, Token, UserData
from auth_service.src.application.login_service import AuthService
from auth_service.src.presentation.dependencies import get_service, get_current_user

router = APIRouter()


@router.post("/register", response_model=UserRead, status_code=201)
async def register(
    user_in: UserCreate,
    background_tasks: BackgroundTasks,
    auth_service: AuthService = Depends(get_service('auth'))
):
    return await auth_service.register_user(user_in, background_tasks)


@router.post("/login", response_model=Token)
async def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    user_agent: str | None = Header(default=None, alias="User-Agent"),
    auth_service: AuthService = Depends(get_service('auth'))
):
    return await auth_service.authenticate_user(
        email=form_data.username,
        password=form_data.password,
        fingerprint=user_agent
    )


@router.post("/refresh")
async def refresh(
    refresh_token: str = Body(embed=True),
    user_agent: str | None = Header(default=None, alias="User-Agent"),
    auth_service: AuthService = Depends(get_service('auth'))
):
    return await auth_service.refresh_session(refresh_token, fingerprint=user_agent)


@router.get("/verify")
async def verify(
    token: str,
    auth_service: AuthService = Depends(get_service('auth'))
):
    return await auth_service.verify_user(token)


@router.delete("/logout")
async def logout(
    refresh_token: str,
    current_user: UserData = Depends(get_current_user),
    auth_service: AuthService = Depends(get_service('auth'))
):
    return await auth_service.logout(refresh_token, current_user.id)

@router.delete("/logout-all")
async def logout_all(
    current_user: UserData = Depends(get_current_user),
    auth_service: AuthService = Depends(get_service('auth'))
):
    return await auth_service.logout_all_sessions(current_user.id)
