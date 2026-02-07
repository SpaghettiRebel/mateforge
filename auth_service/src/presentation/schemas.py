from pydantic import BaseModel, EmailStr, field_validator
from datetime import datetime
import re
from uuid import UUID


class UserAuthBase(BaseModel):
    email: EmailStr


class UserCreate(UserAuthBase):
    password: str
    username: str

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

    class Config:
        from_attributes = True


class UserData(UserRead, UserAuthBase):
    created_at: datetime

    class Config:
        from_attributes = True


class Token(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str
