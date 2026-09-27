import logging
import uuid

from redis.asyncio import Redis

from app.core.config import settings

logger = logging.getLogger(__name__)

_redis: Redis | None = None
_LOCK_KEY = "locks:skinport-sync"
_LOCK_TTL_SECONDS = 300
_RELEASE_SCRIPT = """
if redis.call("get", KEYS[1]) == ARGV[1] then
    return redis.call("del", KEYS[1])
end
return 0
"""


def get_redis() -> Redis:
    global _redis
    if _redis is None:
        _redis = Redis.from_url(settings.redis_url, decode_responses=True)
    return _redis


async def close_redis() -> None:
    global _redis
    if _redis is not None:
        await _redis.aclose()
        _redis = None


async def acquire_price_lock() -> str | None:
    token = str(uuid.uuid4())
    try:
        acquired = await get_redis().set(_LOCK_KEY, token, nx=True, ex=_LOCK_TTL_SECONDS)
    except Exception as exc:
        logger.warning("price lock unavailable, continuing in this process: %s", exc)
        return "local"
    if not acquired:
        return None
    return token


async def release_price_lock(token: str) -> None:
    if token == "local":
        return
    try:
        await get_redis().eval(_RELEASE_SCRIPT, 1, _LOCK_KEY, token)
    except Exception as exc:
        logger.warning("price lock release failed: %s", exc)
