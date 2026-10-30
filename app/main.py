from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.api.router import router
from app.cache.prices import close_redis
from app.core.logging import setup_logging
from app.db.session import engine


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    setup_logging()
    yield
    await close_redis()
    await engine.dispose()


app = FastAPI(title="CSROI", version="0.1.0", lifespan=lifespan)
app.include_router(router, prefix="/api/v1")


@app.get("/")
async def root() -> dict[str, str]:
    return {"service": "csroi", "docs": "/docs"}
