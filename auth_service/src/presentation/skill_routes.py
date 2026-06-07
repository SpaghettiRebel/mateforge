from fastapi import APIRouter, Depends, Query, status

from auth_service.src.application.skill_service import SkillService
from auth_service.src.presentation.dependencies import get_current_user, get_skill_service
from auth_service.src.presentation.schemas import SkillCreate, SkillRead, UserData

router = APIRouter()


@router.get("/", response_model=list[SkillRead])
async def list_skills(
    search: str | None = Query(default=None, min_length=1, max_length=50),
    group: str | None = Query(default=None, min_length=1, max_length=30),
    page: int = Query(default=1, ge=1),
    limit: int = Query(default=50, ge=1, le=100),
    service: SkillService = Depends(get_skill_service),
):
    return await service.list_skills(
        search=search,
        group=group,
        page=page,
        limit=limit,
    )


@router.post("/", response_model=SkillRead, status_code=status.HTTP_201_CREATED)
async def create_skill(
    payload: SkillCreate,
    _: UserData = Depends(get_current_user),
    service: SkillService = Depends(get_skill_service),
):
    return await service.create_skill(payload)
