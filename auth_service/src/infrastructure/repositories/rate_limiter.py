from redis.asyncio import Redis
from fastapi import HTTPException, status


class RateLimiter:
    def __init__(self, redis: Redis):
        self.redis = redis

    async def check_limit(self, key: str, limit: int):
        redis_key = f"limiter:{key}"

        current_count = await self.redis.get(redis_key)

        if current_count and int(current_count) >= limit:
            ttl = await self.redis.ttl(redis_key)
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail=f"Too many attempts. Try again in {ttl} seconds."
            )

    async def increment(self, key: str, window_seconds: int):
        redis_key = f"limiter:{key}"

        async with self.redis.pipeline() as pipe:
            await pipe.incr(redis_key)

            current_ttl = await self.redis.ttl(redis_key)
            if current_ttl == -1 or current_ttl == -2:  # Ключа нет или нет TTL
                await pipe.expire(redis_key, window_seconds)

            await pipe.execute()

    async def reset(self, key: str):
        redis_key = f"limiter:{key}"
        await self.redis.delete(redis_key)