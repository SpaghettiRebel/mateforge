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

    APP_HOST: str = "0.0.0.0"
    APP_PORT: int = 8000
    GRPC_PORT: int = 50051
    LOG_LEVEL: str = "info"

    REDIS_HOST: str
    REDIS_PORT: int
    REDIS_PASSWORD: str | None = None
    REDIS_DB: int = 0

    JWT_SECRET: str = Field(min_length=32)
    JWT_ALGORITHM: Literal["HS256"] = "HS256"
    JWT_ISSUER: str = "mateforge-auth"
    JWT_AUDIENCE: str = "mateforge-api"
    AUTH_ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    VERIFY_ACCESS_TOKEN_EXPIRE_HOURS: int = 12
    REFRESH_TOKEN_EXPIRE_DAYS: int = 30

    MAIL_USERNAME: str
    MAIL_PASSWORD: str
    MAIL_FROM: str
    MAIL_SERVER: str = "smtp.gmail.com"
    MAIL_PORT: int = 587
    MAIL_STARTTLS: bool = True
    MAIL_SSL_TLS: bool = False

    PUBLIC_APP_URL: str = "http://localhost:8000"
    ALLOWED_ORIGINS: list[str] = ["http://localhost:3000"]
    GRPC_SERVICE_TOKEN: str = Field(min_length=32)

    @field_validator("PUBLIC_APP_URL")
    @classmethod
    def normalize_public_url(cls, value: str) -> str:
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

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


settings = Settings()
