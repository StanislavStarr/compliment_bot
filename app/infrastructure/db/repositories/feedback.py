import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.feedback.enums import ReactionType
from app.domain.messages.constants import MAX_RECENT_DISLIKE_REASONS_IN_PROMPT
from app.infrastructure.db.models.feedback import Feedback
from app.infrastructure.db.models.messages import GeneratedMessage


class FeedbackRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def list_recent_dislike_reasons(
        self, user_id: uuid.UUID, limit: int = MAX_RECENT_DISLIKE_REASONS_IN_PROMPT
    ) -> list[str]:
        result = await self._session.execute(
            select(Feedback.reason_code)
            .join(GeneratedMessage, Feedback.message_id == GeneratedMessage.id)
            .where(
                GeneratedMessage.user_id == user_id,
                Feedback.reaction == ReactionType.DISLIKED,
                Feedback.reason_code.is_not(None),
            )
            .order_by(Feedback.created_at.desc())
            .limit(limit)
        )
        return [row for row in result.scalars().all() if row]
