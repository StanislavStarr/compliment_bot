from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from app.domain.messages.enums import MessageType


def genre_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="Короткие комплименты",
                    callback_data=f"genre:{MessageType.COMPLIMENT.value}",
                )
            ],
            [
                InlineKeyboardButton(
                    text="Слова поддержки", callback_data=f"genre:{MessageType.SUPPORT.value}"
                )
            ],
        ]
    )


def address_mode_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="На «ты»", callback_data="addr:informal"),
                InlineKeyboardButton(text="На «вы»", callback_data="addr:formal"),
            ]
        ]
    )


def summary_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="✅ Всё верно, получить ссылку", callback_data="summary:confirm"
                )
            ],
            [InlineKeyboardButton(text="✏️ Изменить", callback_data="summary:edit")],
        ]
    )


def author_edit_menu_keyboard(*, include_support: bool) -> InlineKeyboardMarkup:
    sections = [
        ("genre", "Тип сообщений"),
        ("recipient", "Ник адресата"),
        ("address_mode", "Обращение"),
        ("qualities", "Качества"),
        ("topics", "Темы"),
    ]
    if include_support:
        sections.append(("support", "Способ поддержки"))
    sections.extend(
        [
            ("blocked", "Нежелательные темы"),
            ("style_examples", "Примеры фраз"),
            ("portrait_notes", "Портрет своими словами"),
        ]
    )
    rows = [
        [InlineKeyboardButton(text=label, callback_data=f"edit:{code}")] for code, label in sections
    ]
    rows.append([InlineKeyboardButton(text="⬅️ Назад к резюме", callback_data="edit:back")])
    return InlineKeyboardMarkup(inline_keyboard=rows)
