from fastapi import HTTPException, status
from redis.asyncio import Redis


class RateLimiter:
    _INCREMENT_SCRIPT = """
    local count = redis.call('INCR', KEYS[1])
    if count == 1 then
        redis.call('EXPIRE', KEYS[1], ARGV[1])
    end
    return {count, redis.call('TTL', KEYS[1])}
    """

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

    async def increment(self, key: str, window_seconds: int) -> tuple[int, int]:
        redis_key = f"limiter:{key}"
        count, ttl = await self.redis.eval(
            self._INCREMENT_SCRIPT,
            1,
            redis_key,
            window_seconds,
        )
        return int(count), int(ttl)

    async def reset(self, key: str):
        redis_key = f"limiter:{key}"
        await self.redis.delete(redis_key)
