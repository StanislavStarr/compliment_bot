import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.profiles.enums import StyleExampleSource
from app.infrastructure.db.models.profiles import StyleExample


class StyleExampleRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def list_active_for_user(self, user_id: uuid.UUID) -> list[StyleExample]:
        result = await self._session.execute(
            select(StyleExample).where(
                StyleExample.user_id == user_id, StyleExample.is_active.is_(True)
            )
        )
        return list(result.scalars().all())

    async def add(
        self,
        user_id: uuid.UUID,
        text: str,
        source: StyleExampleSource = StyleExampleSource.ONBOARDING,
    ) -> StyleExample:
        example = StyleExample(user_id=user_id, text=text, source=source)
        self._session.add(example)
        await self._session.flush()
        return example
