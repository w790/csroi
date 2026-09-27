import asyncio
import logging
from datetime import datetime, timezone

from apscheduler.schedulers.asyncio import AsyncIOScheduler

from app.core.config import settings
from app.jobs.tasks import run_catalog, run_price_sync

logger = logging.getLogger(__name__)


def create_scheduler() -> AsyncIOScheduler:
    scheduler = AsyncIOScheduler(timezone="UTC")
    scheduler.add_job(
        _safe(run_price_sync),
        "interval",
        minutes=settings.price_refresh_minutes,
        next_run_time=datetime.now(timezone.utc),
        id="sync_prices",
        replace_existing=True,
        max_instances=1,
        coalesce=True,
    )
    scheduler.add_job(
        _safe(run_catalog),
        "cron",
        hour=3,
        minute=10,
        id="sync_catalog",
        replace_existing=True,
        max_instances=1,
        coalesce=True,
    )
    scheduler.add_job(
        _safe(run_catalog),
        "date",
        run_date=datetime.now(timezone.utc),
        id="sync_catalog_on_start",
        replace_existing=True,
    )
    return scheduler


def _safe(func):
    async def wrapper() -> None:
        try:
            await func()
        except Exception:
            logger.exception("job %s failed", func.__name__)

    return wrapper


async def _main() -> None:
    from app.core.logging import setup_logging

    setup_logging()
    scheduler = create_scheduler()
    scheduler.start()
    logger.info(
        "worker started, prices every %s min, catalog daily at 03:10 UTC",
        settings.price_refresh_minutes,
    )
    try:
        await asyncio.Event().wait()
    finally:
        scheduler.shutdown(wait=False)


if __name__ == "__main__":
    asyncio.run(_main())
