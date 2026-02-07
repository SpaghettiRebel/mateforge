from redis.asyncio import Redis, ConnectionPool
from auth_service.src.infrastructure.config import settings

pool = ConnectionPool.from_url(
    settings.REDIS_URL,
    decode_responses=True
)


def get_redis_client() -> Redis:
    return Redis(connection_pool=pool)
