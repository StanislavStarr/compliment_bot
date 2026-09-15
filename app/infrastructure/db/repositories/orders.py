import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.orders.enums import OPEN_ORDER_STATUSES, OrderStatus
from app.infrastructure.db.models.orders import Order


class OrderRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_id(self, order_id: uuid.UUID) -> Order | None:
        return await self._session.get(Order, order_id)

    async def get_open_for_author(self, author_id: uuid.UUID) -> Order | None:
        result = await self._session.execute(
            select(Order).where(Order.author_id == author_id, Order.status.in_(OPEN_ORDER_STATUSES))
        )
        return result.scalar_one_or_none()

    async def get_open_for_recipient(self, recipient_user_id: uuid.UUID) -> Order | None:
        result = await self._session.execute(
            select(Order).where(
                Order.recipient_user_id == recipient_user_id,
                Order.status.in_(OPEN_ORDER_STATUSES),
            )
        )
        return result.scalar_one_or_none()

    async def get_active_for_recipient(self, recipient_user_id: uuid.UUID) -> Order | None:
        result = await self._session.execute(
            select(Order).where(
                Order.recipient_user_id == recipient_user_id,
                Order.status == OrderStatus.ACTIVE,
            )
        )
        return result.scalar_one_or_none()

    async def get_for_generation(self, user_id: uuid.UUID) -> Order | None:
        """Сначала активный заказ, где user — адресат; иначе открытый заказ автора."""
        recipient_order = await self.get_active_for_recipient(user_id)
        if recipient_order is not None:
            return recipient_order
        return await self.get_open_for_author(user_id)

    async def create_draft(self, author_id: uuid.UUID) -> Order:
        order = Order(author_id=author_id, status=OrderStatus.DRAFT)
        self._session.add(order)
        await self._session.flush()
        return order
