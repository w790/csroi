from collections.abc import AsyncIterator

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.db.session import SessionLocal
from app.repositories.catalog import CatalogRepository
from app.repositories.prices import PriceRepository
from app.services.case_query import CaseQueryService


async def get_session() -> AsyncIterator[AsyncSession]:
    async with SessionLocal() as session:
        yield session


def get_case_query_service(session: AsyncSession = Depends(get_session)) -> CaseQueryService:
    catalog = CatalogRepository(session)
    prices = PriceRepository(session)
    return CaseQueryService(
        catalog,
        prices,
        currency=settings.skinport_currency,
        key_price=settings.key_price_usd,
    )
