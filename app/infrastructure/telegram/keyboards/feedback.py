import uuid

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from app.domain.feedback.constants import DISLIKE_REASON_LABELS


def _hex(message_id: uuid.UUID) -> str:
    return message_id.hex


def feedback_keyboard(message_id: uuid.UUID) -> InlineKeyboardMarkup:
    token = _hex(message_id)
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="Нравится", callback_data=f"fb:l:{token}"),
                InlineKeyboardButton(text="Повторяется", callback_data=f"fb:p:{token}"),
                InlineKeyboardButton(text="Не нравится", callback_data=f"fb:d:{token}"),
            ]
        ]
    )


def dislike_reasons_keyboard(message_id: uuid.UUID) -> InlineKeyboardMarkup:
    token = _hex(message_id)
    rows = [
        [InlineKeyboardButton(text=label, callback_data=f"fb:r:{token}:{reason.value}")]
        for reason, label in DISLIKE_REASON_LABELS.items()
    ]
    rows.append([InlineKeyboardButton(text="Пропустить", callback_data=f"fb:s:{token}")])
    return InlineKeyboardMarkup(inline_keyboard=rows)
