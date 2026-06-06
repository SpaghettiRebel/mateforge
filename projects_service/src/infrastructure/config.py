from typing import Literal
from urllib.parse import quote_plus

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    DB_HOST: str
    DB_PORT: int
    DB_USER: str
    DB_PASS: str
    DB_NAME: str

    REDIS_HOST: str
    REDIS_PORT: int
    REDIS_PASSWORD: str | None = None
    REDIS_DB: int = 0

    JWT_SECRET: str = Field(min_length=32)
    JWT_ALGORITHM: Literal["HS256"] = "HS256"
    JWT_ISSUER: str = "mateforge-auth"
    JWT_AUDIENCE: str = "mateforge-api"
    AUTH_ACCESS_TOKEN_EXPIRE_MINUTES: int = 30

    USERS_SERVICE_URL: str
    AUTH_GRPC_HOST: str = "auth_service"
    AUTH_GRPC_PORT: int = 50051
    AUTH_GRPC_TIMEOUT_SECONDS: float = Field(default=2.0, gt=0, le=10)
    GRPC_SERVICE_TOKEN: str = Field(min_length=32)
    ALLOWED_ORIGINS: list[str] = ["http://localhost:3000"]

    @field_validator("USERS_SERVICE_URL")
    @classmethod
    def normalize_users_service_url(cls, value: str) -> str:
        if not value.startswith(("http://", "https://")):
            value = f"http://{value}"
        return value.rstrip("/")

    @property
    def DATABASE_URL_ASYNCPG(self):
        user = quote_plus(self.DB_USER)
        password = quote_plus(self.DB_PASS)
        return f"postgresql+asyncpg://{user}:{password}@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}"

    @property
    def REDIS_URL(self):
        credentials = f":{quote_plus(self.REDIS_PASSWORD)}@" if self.REDIS_PASSWORD else ""
        return f"redis://{credentials}{self.REDIS_HOST}:{self.REDIS_PORT}/{self.REDIS_DB}"

    @property
    def AUTH_LOGIN_URL(self):
        return f"{self.USERS_SERVICE_URL}/auth/login"

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


settings = Settings()
