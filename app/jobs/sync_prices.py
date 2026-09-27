import asyncio

from app.jobs.tasks import run_price_sync

if __name__ == "__main__":
    asyncio.run(run_price_sync())
