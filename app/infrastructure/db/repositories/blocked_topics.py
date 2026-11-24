import uuid

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.infrastructure.db.models.profiles import BlockedTopic


class BlockedTopicRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def list_for_order(self, order_id: uuid.UUID) -> list[BlockedTopic]:
        result = await self._session.execute(
            select(BlockedTopic).where(BlockedTopic.order_id == order_id)
        )
        return list(result.scalars().all())

    async def replace_for_order(
        self,
        order_id: uuid.UUID,
        topic_codes: list[str],
        custom_text: str | None,
        is_sensitive: bool,
    ) -> None:
        await self._session.execute(delete(BlockedTopic).where(BlockedTopic.order_id == order_id))
        for code in topic_codes:
            self._session.add(BlockedTopic(order_id=order_id, topic_code=code))
        if custom_text:
            self._session.add(
                BlockedTopic(
                    order_id=order_id,
                    custom_text=custom_text,
                    is_sensitive=is_sensitive,
                )
            )
        await self._session.flush()
