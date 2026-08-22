import uuid
from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.application.feedback.service import (
    FeedbackAlreadyExistsError,
    FeedbackNotFoundError,
    FeedbackService,
)
from app.domain.feedback.enums import ReactionType
from app.domain.profiles.enums import StyleExampleSource


def _service() -> tuple[FeedbackService, AsyncMock, AsyncMock, AsyncMock, AsyncMock]:
    session = AsyncMock()
    service = FeedbackService(session)
    messages = AsyncMock()
    feedback = AsyncMock()
    style_examples = AsyncMock()
    bind: Any = service
    bind.messages = messages
    bind.feedback = feedback
    bind.style_examples = style_examples
    return service, session, messages, feedback, style_examples


def _user() -> MagicMock:
    user = MagicMock()
    user.id = uuid.uuid4()
    return user


def _message(user_id: uuid.UUID, text: str = "Ты сегодня спокойна и собрана.") -> MagicMock:
    message = MagicMock()
    message.user_id = user_id
    message.text = text
    return message


async def test_like_saves_text_as_style_example() -> None:
    service, session, messages, feedback, style_examples = _service()
    user = _user()
    message_id = uuid.uuid4()
    messages.get_by_id.return_value = _message(user.id)
    feedback.get_by_message_id.return_value = None
    created = MagicMock()
    feedback.create.return_value = created

    result = await service.submit(user, message_id, ReactionType.LIKED)

    assert result is created
    style_examples.add.assert_awaited_once_with(
        user.id, "Ты сегодня спокойна и собрана.", source=StyleExampleSource.LIKED_MESSAGE
    )
    session.commit.assert_awaited_once()


async def test_dislike_does_not_create_style_example() -> None:
    service, session, messages, feedback, style_examples = _service()
    user = _user()
    message_id = uuid.uuid4()
    messages.get_by_id.return_value = _message(user.id)
    feedback.get_by_message_id.return_value = None

    await service.submit(user, message_id, ReactionType.DISLIKED, reason_code="too_sweet")

    style_examples.add.assert_not_awaited()
    feedback.create.assert_awaited_once()
    session.commit.assert_awaited_once()


async def test_duplicate_reaction_is_rejected() -> None:
    service, _session, messages, feedback, _style_examples = _service()
    user = _user()
    message_id = uuid.uuid4()
    messages.get_by_id.return_value = _message(user.id)
    feedback.get_by_message_id.return_value = MagicMock()

    with pytest.raises(FeedbackAlreadyExistsError):
        await service.submit(user, message_id, ReactionType.REPEATED)

    feedback.create.assert_not_awaited()


async def test_foreign_message_is_rejected() -> None:
    service, _session, messages, feedback, _style_examples = _service()
    user = _user()
    message_id = uuid.uuid4()
    messages.get_by_id.return_value = _message(uuid.uuid4())
    feedback.get_by_message_id.return_value = None

    with pytest.raises(FeedbackNotFoundError):
        await service.submit(user, message_id, ReactionType.LIKED)

    feedback.create.assert_not_awaited()
