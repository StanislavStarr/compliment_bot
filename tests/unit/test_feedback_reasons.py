import uuid

from app.domain.feedback.constants import DISLIKE_REASON_LABELS
from app.domain.profiles.enums import DislikeReason
from app.infrastructure.telegram.keyboards.feedback import (
    dislike_reasons_keyboard,
    feedback_keyboard,
)


def test_dislike_reason_labels_cover_enum() -> None:
    assert set(DISLIKE_REASON_LABELS) == set(DislikeReason)


def test_feedback_callback_data_fits_telegram_limit() -> None:
    message_id = uuid.uuid4()
    keyboards = [feedback_keyboard(message_id), dislike_reasons_keyboard(message_id)]
    for keyboard in keyboards:
        for row in keyboard.inline_keyboard:
            for button in row:
                assert button.callback_data is not None
                assert len(button.callback_data.encode()) <= 64
