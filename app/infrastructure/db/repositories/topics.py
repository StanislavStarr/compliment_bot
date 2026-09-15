import uuid

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.topics.enums import MAX_ACTIVE_TOPICS_PER_USER
from app.infrastructure.db.models.topics import OrderTopic, Topic


class TopicRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def list_all(self) -> list[Topic]:
        result = await self._session.execute(select(Topic).order_by(Topic.code))
        return list(result.scalars().all())

    async def get_by_code(self, code: str) -> Topic | None:
        result = await self._session.execute(select(Topic).where(Topic.code == code))
        return result.scalar_one_or_none()


class OrderTopicRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def list_active_for_order(self, order_id: uuid.UUID) -> list[OrderTopic]:
        result = await self._session.execute(
            select(OrderTopic)
            .where(OrderTopic.order_id == order_id, OrderTopic.is_active.is_(True))
            .order_by(OrderTopic.position)
        )
        return list(result.scalars().all())

    async def replace_for_order(self, order_id: uuid.UUID, topic_ids: list[uuid.UUID]) -> None:
        if len(topic_ids) > MAX_ACTIVE_TOPICS_PER_USER:
            raise ValueError(f"Максимум {MAX_ACTIVE_TOPICS_PER_USER} активных тем на заказ")
        await self._session.execute(delete(OrderTopic).where(OrderTopic.order_id == order_id))
        for position, topic_id in enumerate(topic_ids):
            self._session.add(OrderTopic(order_id=order_id, topic_id=topic_id, position=position))
        await self._session.flush()
