import asyncio

from app.jobs.tasks import run_catalog

if __name__ == "__main__":
    asyncio.run(run_catalog())
