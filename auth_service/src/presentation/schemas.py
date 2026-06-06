import re
from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator


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


class UserRead(BaseModel):
    id: UUID
    username: str
    bio: str | None = None
    followers_count: int
    following_count: int

    model_config = ConfigDict(from_attributes=True)

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
