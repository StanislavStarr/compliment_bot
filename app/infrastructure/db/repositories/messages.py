import uuid
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.messages.constants import MAX_RECENT_MESSAGES_IN_PROMPT
from app.domain.messages.enums import MessageSource, MessageType
from app.infrastructure.db.models.messages import GeneratedMessage


class GeneratedMessageRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def list_recent_for_user(
        self, user_id: uuid.UUID, limit: int = MAX_RECENT_MESSAGES_IN_PROMPT
    ) -> list[GeneratedMessage]:
        result = await self._session.execute(
            select(GeneratedMessage)
            .where(GeneratedMessage.user_id == user_id)
            .order_by(GeneratedMessage.generated_at.desc())
            .limit(limit)
        )
        return list(result.scalars().all())

    async def get_last_for_user(self, user_id: uuid.UUID) -> GeneratedMessage | None:
        result = await self._session.execute(
            select(GeneratedMessage)
            .where(GeneratedMessage.user_id == user_id)
            .order_by(GeneratedMessage.generated_at.desc())
            .limit(1)
        )
        return result.scalar_one_or_none()

    async def create(
        self,
        *,
        delivery_id: uuid.UUID,
        user_id: uuid.UUID,
        text: str | None,
        message_type: MessageType,
        theme: str,
        semantic_key: str,
        source: MessageSource,
        generated_at: datetime,
        provider: str | None = None,
        model: str | None = None,
        prompt_version_id: uuid.UUID | None = None,
        input_tokens: int | None = None,
        output_tokens: int | None = None,
        validation_status: str | None = None,
    ) -> GeneratedMessage:
        """Персист сообщения привязан к `delivery_id` — вызывается из
        delivery-таска (Этап 5), а не из `GenerationService` напрямую."""
        message = GeneratedMessage(
            delivery_id=delivery_id,
            user_id=user_id,
            text=text,
            type=message_type,
            theme=theme,
            semantic_key=semantic_key,
            source=source,
            provider=provider,
            model=model,
            prompt_version_id=prompt_version_id,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            validation_status=validation_status,
            generated_at=generated_at,
        )
        self._session.add(message)
        await self._session.flush()
        return message
