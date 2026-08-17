import uuid

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.infrastructure.db.models.profiles import Quality, UserQuality


class QualityRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def list_all(self) -> list[Quality]:
        result = await self._session.execute(select(Quality).order_by(Quality.code))
        return list(result.scalars().all())


class UserQualityRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def list_for_user(self, user_id: uuid.UUID) -> list[UserQuality]:
        result = await self._session.execute(
            select(UserQuality).where(UserQuality.user_id == user_id)
        )
        return list(result.scalars().all())

    async def replace_for_user(
        self,
        user_id: uuid.UUID,
        quality_ids: list[uuid.UUID],
        custom_text: str | None,
        is_sensitive: bool,
    ) -> None:
        """Полностью заменяет набор качеств пользователя — шаг онбординга
        не накопительный, повторное прохождение перезаписывает выбор."""
        await self._session.execute(delete(UserQuality).where(UserQuality.user_id == user_id))
        for quality_id in quality_ids:
            self._session.add(UserQuality(user_id=user_id, quality_id=quality_id))
        if custom_text:
            self._session.add(
                UserQuality(
                    user_id=user_id,
                    custom_text=custom_text,
                    is_sensitive=is_sensitive,
                    excluded_from_generation=is_sensitive,
                )
            )
        await self._session.flush()
