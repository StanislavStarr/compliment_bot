import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.infrastructure.db.models.profiles import Profile


class ProfileRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_user_id(self, user_id: uuid.UUID) -> Profile | None:
        result = await self._session.execute(select(Profile).where(Profile.user_id == user_id))
        return result.scalar_one_or_none()

    async def get_or_create(self, user_id: uuid.UUID) -> Profile:
        profile = await self.get_by_user_id(user_id)
        if profile is not None:
            return profile
        profile = Profile(user_id=user_id)
        self._session.add(profile)
        await self._session.flush()
        return profile

    async def set_support_description(
        self, user_id: uuid.UUID, text: str | None, is_sensitive: bool
    ) -> None:
        profile = await self.get_or_create(user_id)
        profile.support_description = text
        profile.sensitive_input_present = profile.sensitive_input_present or is_sensitive
