from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from app.domain.schedules.enums import PERIOD_LABELS, QUICK_PICK_EXACT_TIMES, ScheduleMode
from app.domain.users.constants import COMMON_TIMEZONES, TIMEZONE_MANUAL_OPTION_CODE


def recipient_consent_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="Да, хочу получать", callback_data="invite:accept"),
                InlineKeyboardButton(text="Нет, спасибо", callback_data="invite:decline"),
            ]
        ]
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
