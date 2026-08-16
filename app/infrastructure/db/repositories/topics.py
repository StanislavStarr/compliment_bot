from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.infrastructure.db.models.topics import Topic


class TopicRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def list_all(self) -> list[Topic]:
        result = await self._session.execute(select(Topic).order_by(Topic.code))
        return list(result.scalars().all())

    async def get_by_code(self, code: str) -> Topic | None:
        result = await self._session.execute(select(Topic).where(Topic.code == code))
        return result.scalar_one_or_none()
