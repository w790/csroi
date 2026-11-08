import logging

from redis.asyncio import Redis
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)

STATUS_OK = "ok"
STATUS_DOWN = "down"
STATUS_DEGRADED = "degraded"


async def check_database(session: AsyncSession) -> str:
    try:
        await session.execute(text("SELECT 1"))
    except Exception as exc:
        logger.warning("database unavailable: %s", exc)
        return STATUS_DOWN
    return STATUS_OK


async def check_redis(redis: Redis) -> str:
    try:
        await redis.ping()
    except Exception as exc:
        logger.warning("redis unavailable: %s", exc)
        return STATUS_DOWN
    return STATUS_OK


def overall_status(database_status: str, redis_status: str) -> str:
    if database_status == STATUS_OK and redis_status == STATUS_OK:
        return STATUS_OK
    return STATUS_DEGRADED
