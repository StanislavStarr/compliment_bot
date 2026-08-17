import uuid

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.infrastructure.db.models.profiles import SupportPreference


class SupportPreferenceRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def list_for_user(self, user_id: uuid.UUID) -> list[SupportPreference]:
        result = await self._session.execute(
            select(SupportPreference).where(SupportPreference.user_id == user_id)
        )
        return list(result.scalars().all())

    async def replace_for_user(
        self,
        user_id: uuid.UUID,
        preference_codes: list[str],
        custom_text: str | None,
        is_sensitive: bool,
    ) -> None:
        await self._session.execute(
            delete(SupportPreference).where(SupportPreference.user_id == user_id)
        )
        for code in preference_codes:
            self._session.add(SupportPreference(user_id=user_id, preference_code=code))
        if custom_text:
            self._session.add(
                SupportPreference(
                    user_id=user_id,
                    custom_text=custom_text,
                    is_sensitive=is_sensitive,
                    excluded_from_generation=is_sensitive,
                )
            )
        await self._session.flush()
