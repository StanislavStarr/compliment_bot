import hashlib

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.infrastructure.db.models.messages import PromptVersion


class PromptVersionRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_version(self, version: str) -> PromptVersion | None:
        result = await self._session.execute(
            select(PromptVersion).where(PromptVersion.version == version)
        )
        return result.scalar_one_or_none()

    async def get_or_create(self, version: str, system_prompt: str) -> PromptVersion:
        """`system_prompt_hash` фиксирует, каким именно текстом промпта было
        сгенерировано сообщение — полезно при последующем анализе качества,
        даже если строка `version` не менялась."""
        existing = await self.get_by_version(version)
        prompt_hash = hashlib.sha256(system_prompt.encode("utf-8")).hexdigest()
        if existing is not None:
            return existing

        record = PromptVersion(version=version, system_prompt_hash=prompt_hash, is_active=True)
        self._session.add(record)
        await self._session.flush()
        return record
