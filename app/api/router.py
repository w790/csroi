from fastapi import APIRouter

from app.api.v1 import cases, health

router = APIRouter()
router.include_router(health.router)
router.include_router(cases.router)
