from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup


def author_home_keyboard(*, cancellable: bool) -> InlineKeyboardMarkup:
    rows: list[list[InlineKeyboardButton]] = []
    if cancellable:
        rows.append([InlineKeyboardButton(text="🚫 Отменить заказ", callback_data="order:cancel")])
    rows.append([InlineKeyboardButton(text="ℹ️ О сервисе", callback_data="settings:info")])
    rows.append([InlineKeyboardButton(text="🗑 Удалить профиль", callback_data="settings:delete")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def recipient_home_keyboard(*, paused: bool, is_admin: bool) -> InlineKeyboardMarkup:
    rows: list[list[InlineKeyboardButton]] = [
        [InlineKeyboardButton(text="🕐 Изменить время", callback_data="settings:slot")],
        [
            InlineKeyboardButton(
                text="▶️ Возобновить" if paused else "⏸ Приостановить",
                callback_data="settings:resume" if paused else "settings:pause",
            )
        ],
        [InlineKeyboardButton(text="🚫 Больше не получать", callback_data="order:stop")],
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


def stopped_profile_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="ℹ️ О сервисе", callback_data="settings:info")],
            [InlineKeyboardButton(text="🗑 Удалить профиль", callback_data="settings:delete")],
        ]
    )


def confirm_action_keyboard(*, yes: str, no: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="Да, подтвердить", callback_data=yes)],
            [InlineKeyboardButton(text="Отмена", callback_data=no)],
        ]
    )


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
