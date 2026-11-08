import logging
import uuid

from app.cache.redis_client import get_redis

logger = logging.getLogger(__name__)

LOCAL_LOCK_TOKEN = "local"
_LOCK_KEY = "locks:skinport-sync"
_LOCK_TTL_SECONDS = 300
_RELEASE_SCRIPT = """
if redis.call("get", KEYS[1]) == ARGV[1] then
    return redis.call("del", KEYS[1])
end
return 0
"""


async def acquire_price_lock() -> str | None:
    try:
        return await _set_lock(str(uuid.uuid4()))
    except Exception as exc:
        logger.warning("price lock unavailable, continuing in this process: %s", exc)
        return LOCAL_LOCK_TOKEN


async def release_price_lock(token: str) -> None:
    if token == LOCAL_LOCK_TOKEN:
        return
    try:
        await get_redis().eval(_RELEASE_SCRIPT, 1, _LOCK_KEY, token)
    except Exception as exc:
        logger.warning("price lock release failed: %s", exc)


async def _set_lock(token: str) -> str | None:
    acquired = await get_redis().set(_LOCK_KEY, token, nx=True, ex=_LOCK_TTL_SECONDS)
    if not acquired:
        return None
    return token
