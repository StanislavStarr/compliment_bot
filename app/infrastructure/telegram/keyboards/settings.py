from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup


def settings_keyboard(*, paused: bool, is_admin: bool) -> InlineKeyboardMarkup:
    rows = [
        [InlineKeyboardButton(text="✏️ Изменить профиль", callback_data="settings:edit")],
        [
            InlineKeyboardButton(
                text="▶️ Возобновить" if paused else "⏸ Приостановить",
                callback_data="settings:resume" if paused else "settings:pause",
            )
        ],
        [InlineKeyboardButton(text="ℹ️ О сервисе", callback_data="settings:info")],
        [InlineKeyboardButton(text="🗑 Удалить профиль", callback_data="settings:delete")],
    ]
    if is_admin:
        rows.insert(
            1,
            [
                InlineKeyboardButton(
                    text="⚡️ Получить сообщение сейчас", callback_data="settings:generate"
                )
            ],
        )
    return InlineKeyboardMarkup(inline_keyboard=rows)


def delete_confirm_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="Да, удалить навсегда", callback_data="settings:delete_confirm"
                )
            ],
            [InlineKeyboardButton(text="Отмена", callback_data="settings:delete_cancel")],
        ]
    )
