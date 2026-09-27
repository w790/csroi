import logging

from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_session
from app.cache.prices import get_redis
from app.schemas.health import HealthOut

logger = logging.getLogger(__name__)
router = APIRouter(tags=["health"])


@router.get("/health", response_model=HealthOut)
async def health(session: AsyncSession = Depends(get_session)) -> HealthOut:
    database = "ok"
    redis_status = "ok"
    try:
        await session.execute(text("SELECT 1"))
    except Exception as exc:
        logger.warning("database unavailable: %s", exc)
        database = "down"
    try:
        await get_redis().ping()
    except Exception as exc:
        logger.warning("redis unavailable: %s", exc)
        redis_status = "down"
    status = "ok" if database == "ok" and redis_status == "ok" else "degraded"
    return HealthOut(status=status, database=database, redis=redis_status)
