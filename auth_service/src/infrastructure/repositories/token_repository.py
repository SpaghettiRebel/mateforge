from redis.asyncio import Redis

class TokenRepository:
    def __init__(self, redis: Redis):
        self.redis = redis

    async def save_token(self, user_id: str, refresh_token: str, data: str, ttl: int):
        await self.redis.setex(f"refresh_token:{refresh_token}", ttl, data)
        await self.redis.sadd(f"user_sessions:{user_id}", refresh_token)
        await self.redis.expire(f"user_sessions:{user_id}", ttl + 3600)

    async def delete_token(self, user_id: str, refresh_token: str):
        await self.redis.delete(f"refresh_token:{refresh_token}")
        await self.redis.srem(f"user_sessions:{user_id}", refresh_token)

    async def delete_all_user_tokens(self, user_id: str):
        session_key = f"user_sessions:{user_id}"
        tokens = await self.redis.smembers(session_key)

        if tokens:
            keys_to_delete = [f"refresh_token:{t.decode() if isinstance(t, bytes) else t}" for t in tokens]
            await self.redis.delete(*keys_to_delete)

        await self.redis.delete(session_key)

    async def get_token_data(self, refresh_token: str):
        return await self.redis.get(f"refresh_token:{refresh_token}")
