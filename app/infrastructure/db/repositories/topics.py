import uuid

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.topics.enums import MAX_ACTIVE_TOPICS_PER_USER
from app.infrastructure.db.models.topics import Topic, UserTopic


class TopicRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def list_all(self) -> list[Topic]:
        result = await self._session.execute(select(Topic).order_by(Topic.code))
        return list(result.scalars().all())

    async def get_by_code(self, code: str) -> Topic | None:
        result = await self._session.execute(select(Topic).where(Topic.code == code))
        return result.scalar_one_or_none()


class UserTopicRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def list_active_for_user(self, user_id: uuid.UUID) -> list[UserTopic]:
        result = await self._session.execute(
            select(UserTopic)
            .where(UserTopic.user_id == user_id, UserTopic.is_active.is_(True))
            .order_by(UserTopic.position)
        )
        return list(result.scalars().all())

    async def replace_for_user(self, user_id: uuid.UUID, topic_ids: list[uuid.UUID]) -> None:
        if len(topic_ids) > MAX_ACTIVE_TOPICS_PER_USER:
            raise ValueError(f"Максимум {MAX_ACTIVE_TOPICS_PER_USER} активных тем на пользователя")
        await self._session.execute(delete(UserTopic).where(UserTopic.user_id == user_id))
        for position, topic_id in enumerate(topic_ids):
            self._session.add(UserTopic(user_id=user_id, topic_id=topic_id, position=position))
        await self._session.flush()
