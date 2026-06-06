import hashlib

from redis.asyncio import Redis


class TokenRepository:
    _ROTATE_SCRIPT = """
    local data = redis.call('GET', KEYS[1])
    if not data then
        return nil
    end
    redis.call('DEL', KEYS[1])
    redis.call('SREM', KEYS[3], ARGV[1])
    redis.call('SETEX', KEYS[2], ARGV[3], ARGV[2])
    redis.call('SADD', KEYS[3], ARGV[4])
    redis.call('EXPIRE', KEYS[3], ARGV[3] + 3600)
    return data
    """

    def __init__(self, redis: Redis):
        self.redis = redis

    @staticmethod
    def _digest(refresh_token: str) -> str:
        return hashlib.sha256(refresh_token.encode("utf-8")).hexdigest()

    async def save_token(self, user_id: str, refresh_token: str, data: str, ttl: int):
        token_digest = self._digest(refresh_token)
        session_key = f"user_sessions:{user_id}"
        async with self.redis.pipeline(transaction=True) as pipe:
            pipe.setex(f"refresh_token:{token_digest}", ttl, data)
            pipe.sadd(session_key, token_digest)
            pipe.expire(session_key, ttl + 3600)
            await pipe.execute()

    async def delete_token(self, user_id: str, refresh_token: str):
        token_digest = self._digest(refresh_token)
        async with self.redis.pipeline(transaction=True) as pipe:
            pipe.delete(f"refresh_token:{token_digest}")
            pipe.srem(f"user_sessions:{user_id}", token_digest)
            await pipe.execute()

    async def delete_all_user_tokens(self, user_id: str):
        session_key = f"user_sessions:{user_id}"
        tokens = await self.redis.smembers(session_key)

        if tokens:
            keys_to_delete = [
                f"refresh_token:{token.decode() if isinstance(token, bytes) else token}"
                for token in tokens
            ]
            await self.redis.delete(*keys_to_delete)

        await self.redis.delete(session_key)

    async def get_token_data(self, refresh_token: str):
        token_digest = self._digest(refresh_token)
        return await self.redis.get(f"refresh_token:{token_digest}")

    async def rotate_token(
        self,
        user_id: str,
        old_refresh_token: str,
        new_refresh_token: str,
        data: str,
        ttl: int,
    ) -> bool:
        old_digest = self._digest(old_refresh_token)
        new_digest = self._digest(new_refresh_token)
        result = await self.redis.eval(
            self._ROTATE_SCRIPT,
            3,
            f"refresh_token:{old_digest}",
            f"refresh_token:{new_digest}",
            f"user_sessions:{user_id}",
            old_digest,
            data,
            ttl,
            new_digest,
        )
        return result is not None
