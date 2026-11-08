import asyncio

from app.core.logging import setup_logging
from app.jobs.tasks import run_catalog_sync

if __name__ == "__main__":
    setup_logging()
    asyncio.run(run_catalog_sync())
