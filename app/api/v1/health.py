from fastapi import APIRouter, Depends, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_session
from app.cache.redis_client import get_redis
from app.schemas.health import HealthOut
from app.services.health import STATUS_OK, check_database, check_redis, overall_status

router = APIRouter(tags=["health"])


@router.get("/health", response_model=HealthOut)
async def health(
    response: Response,
    session: AsyncSession = Depends(get_session),
) -> HealthOut:
    database_status = await check_database(session)
    redis_status = await check_redis(get_redis())
    if database_status != STATUS_OK:
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    return HealthOut(
        status=overall_status(database_status, redis_status),
        database=database_status,
        redis=redis_status,
    )
