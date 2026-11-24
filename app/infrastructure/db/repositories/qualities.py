import uuid

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.infrastructure.db.models.profiles import OrderQuality, Quality


class QualityRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def list_all(self) -> list[Quality]:
        result = await self._session.execute(select(Quality).order_by(Quality.code))
        return list(result.scalars().all())


class OrderQualityRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def list_for_order(self, order_id: uuid.UUID) -> list[OrderQuality]:
        result = await self._session.execute(
            select(OrderQuality).where(OrderQuality.order_id == order_id)
        )
        return list(result.scalars().all())

    async def replace_for_order(
        self,
        order_id: uuid.UUID,
        quality_ids: list[uuid.UUID],
        custom_text: str | None,
        is_sensitive: bool,
    ) -> None:
        """Полностью заменяет набор качеств заказа — шаг онбординга
        не накопительный, повторное прохождение перезаписывает выбор."""
        await self._session.execute(delete(OrderQuality).where(OrderQuality.order_id == order_id))
        for quality_id in quality_ids:
            self._session.add(OrderQuality(order_id=order_id, quality_id=quality_id))
        if custom_text:
            self._session.add(
                OrderQuality(
                    order_id=order_id,
                    custom_text=custom_text,
                    is_sensitive=is_sensitive,
                    excluded_from_generation=is_sensitive,
                )
            )
        await self._session.flush()
