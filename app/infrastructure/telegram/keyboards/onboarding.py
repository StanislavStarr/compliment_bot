from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from app.domain.schedules.enums import PERIOD_LABELS, QUICK_PICK_EXACT_TIMES, ScheduleMode
from app.domain.users.constants import COMMON_TIMEZONES, TIMEZONE_MANUAL_OPTION_CODE


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


def address_mode_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="На «ты»", callback_data="addr:informal"),
                InlineKeyboardButton(text="На «вы»", callback_data="addr:formal"),
            ]
        ]
    )


def multi_select_keyboard(
    options: list[tuple[str, str]],
    selected: set[str],
    prefix: str,
    done_text: str = "Готово ➡️",
) -> InlineKeyboardMarkup:
    """Клавиатура множественного выбора. `options` — пары (код, подпись).
    Выбранные элементы помечаются галочкой, повторное нажатие снимает выбор."""
    rows = []
    for code, label in options:
        text = f"✅ {label}" if code in selected else label
        rows.append([InlineKeyboardButton(text=text, callback_data=f"{prefix}:toggle:{code}")])
    rows.append([InlineKeyboardButton(text=done_text, callback_data=f"{prefix}:done")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def skip_keyboard(callback_data: str, text: str = "Пропустить") -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[[InlineKeyboardButton(text=text, callback_data=callback_data)]]
    )


def timezone_keyboard() -> InlineKeyboardMarkup:
    rows = [
        [InlineKeyboardButton(text=label, callback_data=f"tz:set:{code}")]
        for code, label in COMMON_TIMEZONES
    ]
    rows.append(
        [
            InlineKeyboardButton(
                text="Другой (ввести вручную)", callback_data=f"tz:{TIMEZONE_MANUAL_OPTION_CODE}"
            )
        ]
    )
    return InlineKeyboardMarkup(inline_keyboard=rows)


def schedule_mode_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="Точное время", callback_data=f"sched_mode:{ScheduleMode.EXACT.value}"
                ),
                InlineKeyboardButton(
                    text="Период дня", callback_data=f"sched_mode:{ScheduleMode.PERIOD.value}"
                ),
            ]
        ]
    )


def exact_time_keyboard() -> InlineKeyboardMarkup:
    rows = [
        [InlineKeyboardButton(text=t, callback_data=f"sched_time:pick:{t}")]
        for t in QUICK_PICK_EXACT_TIMES
    ]
    rows.append(
        [
            InlineKeyboardButton(
                text="Другое время (ввести вручную)", callback_data="sched_time:manual"
            )
        ]
    )
    return InlineKeyboardMarkup(inline_keyboard=rows)


def period_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=label, callback_data=f"sched_period:{period.value}")]
            for period, label in PERIOD_LABELS.items()
        ]
    )


def summary_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="✅ Всё верно", callback_data="summary:confirm")],
            [InlineKeyboardButton(text="✏️ Изменить", callback_data="summary:edit")],
        ]
    )


EDIT_SECTIONS: list[tuple[str, str]] = [
    ("address_mode", "Обращение"),
    ("qualities", "Качества"),
    ("topics", "Темы"),
    ("support", "Способ поддержки"),
    ("blocked", "Нежелательные темы"),
    ("style_examples", "Примеры фраз"),
    ("timezone", "Часовой пояс и время"),
]


def edit_menu_keyboard() -> InlineKeyboardMarkup:
    rows = [
        [InlineKeyboardButton(text=label, callback_data=f"edit:{code}")]
        for code, label in EDIT_SECTIONS
    ]
    rows.append([InlineKeyboardButton(text="⬅️ Назад к резюме", callback_data="edit:back")])
    return InlineKeyboardMarkup(inline_keyboard=rows)
