from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.messages.enums import MessageType
from app.domain.users.enums import AddressMode
from app.infrastructure.db.models.messages import FallbackMessage


class FallbackMessageRepository:
    """Один каталог служит и few-shot референсом для промпта (см.
    `ReferenceExample`), и резервной фразой при отказе AI — оба сценария
    читают одни и те же строки, поэтому отдельной таблицы для примеров нет."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def list_active_for(
        self, topic_code: str, message_type: MessageType, address_mode: AddressMode
    ) -> list[FallbackMessage]:
        result = await self._session.execute(
            select(FallbackMessage).where(
                FallbackMessage.topic_code == topic_code,
                FallbackMessage.type == message_type,
                FallbackMessage.address_mode == address_mode,
                FallbackMessage.is_active.is_(True),
            )
        )
        return list(result.scalars().all())

    async def list_active_for_any_topic(
        self, message_type: MessageType, address_mode: AddressMode
    ) -> list[FallbackMessage]:
        """Последний рубеж защиты: если для темы почему-то нет резервных
        фраз (например, тема добавлена без сидирования fallback)."""
        result = await self._session.execute(
            select(FallbackMessage).where(
                FallbackMessage.type == message_type,
                FallbackMessage.address_mode == address_mode,
                FallbackMessage.is_active.is_(True),
            )
        )
        return list(result.scalars().all())
