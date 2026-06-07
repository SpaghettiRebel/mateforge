import re
from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator, model_validator

from auth_service.src.infrastructure.models import SkillLevel


class UserAuthBase(BaseModel):
    email: EmailStr


class UserCreate(UserAuthBase):
    password: str = Field(min_length=8, max_length=128)
    username: str = Field(min_length=3, max_length=50, pattern=r"^[A-Za-z0-9_.-]+$")

    @field_validator("email")
    @classmethod
    def normalize_email(cls, value: EmailStr) -> str:
        return str(value).strip().lower()

    @field_validator("username")
    @classmethod
    def normalize_username(cls, value: str) -> str:
        return value.strip()

    @field_validator('password')
    @classmethod
    def password_strength(cls, v: str):
        if len(v) < 8:
            raise ValueError('Пароль должен содержать не менее 8 символов')
        if not re.search(r'[A-Z]', v):
            raise ValueError('Пароль должен содержать хотя бы одну заглавную букву')
        if not re.search(r'[a-z]', v):
            raise ValueError('Пароль должен содержать хотя бы одну строчную букву')
        if not re.search(r'\d', v):
            raise ValueError('Пароль должен содержать хотя бы одну цифру')
        return v


class UserLogin(UserAuthBase):
    password: str


class SkillRead(BaseModel):
    id: UUID
    name: str
    slug: str
    group: str

    model_config = ConfigDict(from_attributes=True)


class SkillCreate(BaseModel):
    name: str = Field(min_length=1, max_length=50)
    slug: str = Field(min_length=1, max_length=50, pattern=r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
    group: str = Field(default="hard-skill", min_length=1, max_length=30, pattern=r"^[a-z0-9]+(?:-[a-z0-9]+)*$")

    @field_validator("name", mode="before")
    @classmethod
    def normalize_name(cls, value: Any) -> Any:
        if not isinstance(value, str):
            return value
        return " ".join(value.split())

    @field_validator("slug", "group", mode="before")
    @classmethod
    def normalize_slug_fields(cls, value: Any) -> Any:
        if not isinstance(value, str):
            return value
        return value.strip().lower()


class UserSkillRead(BaseModel):
    skill: SkillRead
    level: SkillLevel

    model_config = ConfigDict(from_attributes=True)


class UserSkillInput(BaseModel):
    skill_id: UUID
    level: SkillLevel = SkillLevel.BEGINNER


class UserSkillsReplace(BaseModel):
    skills: list[UserSkillInput] = Field(default_factory=list, max_length=50)

    @model_validator(mode="after")
    def validate_unique_skills(self):
        skill_ids = [item.skill_id for item in self.skills]
        if len(skill_ids) != len(set(skill_ids)):
            raise ValueError("Duplicate skill_id values are not allowed")
        return self


class UserSkillLevelUpdate(BaseModel):
    level: SkillLevel


class UserRead(BaseModel):
    id: UUID
    username: str
    bio: str | None = None
    followers_count: int
    following_count: int
    skills: list[UserSkillRead] = Field(default_factory=list, validation_alias="skill_links")

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

class UserData(UserRead, UserAuthBase):
    created_at: datetime


class Token(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str


class RefreshTokenRequest(BaseModel):
    refresh_token: str = Field(min_length=32, max_length=512)


class LogoutRequest(RefreshTokenRequest):
    pass


class UserBioUpdate(BaseModel):
    bio: str = Field(max_length=1000)
