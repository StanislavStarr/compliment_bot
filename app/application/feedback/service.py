import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.feedback.enums import ReactionType
from app.domain.profiles.enums import StyleExampleSource
from app.infrastructure.db.models.feedback import Feedback
from app.infrastructure.db.models.users import User
from app.infrastructure.db.repositories.feedback import FeedbackRepository
from app.infrastructure.db.repositories.messages import GeneratedMessageRepository
from app.infrastructure.db.repositories.style_examples import StyleExampleRepository


class FeedbackError(Exception):
    pass


class FeedbackNotFoundError(FeedbackError):
    pass


class FeedbackAlreadyExistsError(FeedbackError):
    pass


class FeedbackService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self.feedback = FeedbackRepository(session)
        self.messages = GeneratedMessageRepository(session)
        self.style_examples = StyleExampleRepository(session)

    async def submit(
        self,
        user: User,
        message_id: uuid.UUID,
        reaction: ReactionType,
        reason_code: str | None = None,
        comment: str | None = None,
    ) -> Feedback:
        """Реакция окончательная (раздел 10 плана): повторно не принимается.
        «Нравится» сохраняет текст как положительный пример стиля."""
        message = await self.messages.get_by_id(message_id)
        if message is None or message.user_id != user.id:
            raise FeedbackNotFoundError("сообщение не найдено")

        existing = await self.feedback.get_by_message_id(message_id)
        if existing is not None:
            raise FeedbackAlreadyExistsError("реакция уже сохранена")

        record = await self.feedback.create(
            message_id=message_id,
            user_id=user.id,
            reaction=reaction,
            reason_code=reason_code,
            comment=comment,
        )
        if reaction is ReactionType.LIKED and message.text:
            await self.style_examples.add(
                user.id, message.text, source=StyleExampleSource.LIKED_MESSAGE
            )
        await self._session.commit()
        return record
