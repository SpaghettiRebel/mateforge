from redis.asyncio import Redis
from typing import Optional


class TokenRepository:
    def __init__(self, redis: Redis):
        self.redis = redis
        self.prefix = "auth_service:refresh_token:"

    async def save_token(self, token: str, data: str, expire_seconds: int):
        key = f"{self.prefix}{token}"
        await self.redis.set(key, data, ex=expire_seconds)

    async def get_token_data(self, token: str) -> Optional[str]:
        key = f"{self.prefix}{token}"
        return await self.redis.get(key)

    async def delete_token(self, token: str):
        key = f"{self.prefix}{token}"
        await self.redis.delete(key)
