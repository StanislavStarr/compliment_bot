from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup


def consent_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="Подтверждаю 18+ и согласен(на)", callback_data="consent:accept"
                )
            ]
        ]
    )


def multi_select_keyboard(
    options: list[tuple[str, str]],
    selected: set[str],
    prefix: str,
    done_text: str = "Готово ➡️",
) -> InlineKeyboardMarkup:
    rows = [
        [
            InlineKeyboardButton(
                text=f"✅ {label}" if code in selected else label,
                callback_data=f"{prefix}:toggle:{code}",
            )
        ]
        for code, label in options
    ]
    rows.append([InlineKeyboardButton(text=done_text, callback_data=f"{prefix}:done")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def skip_keyboard(callback_data: str, text: str = "Пропустить") -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[[InlineKeyboardButton(text=text, callback_data=callback_data)]]
    )
