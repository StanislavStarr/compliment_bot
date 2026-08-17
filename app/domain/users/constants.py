"""Список часовых поясов для быстрого выбора в онбординге. Пользователь также
может ввести произвольный IANA timezone текстом (валидируется через zoneinfo)."""

COMMON_TIMEZONES: list[tuple[str, str]] = [
    ("Europe/Moscow", "Москва (UTC+3)"),
    ("Europe/Kaliningrad", "Калининград (UTC+2)"),
    ("Europe/Samara", "Самара (UTC+4)"),
    ("Asia/Yekaterinburg", "Екатеринбург (UTC+5)"),
    ("Asia/Novosibirsk", "Новосибирск (UTC+7)"),
    ("Asia/Krasnoyarsk", "Красноярск (UTC+7)"),
    ("Asia/Irkutsk", "Иркутск (UTC+8)"),
    ("Asia/Vladivostok", "Владивосток (UTC+10)"),
    ("Europe/Kyiv", "Киев (UTC+2)"),
    ("Europe/Minsk", "Минск (UTC+3)"),
    ("Asia/Almaty", "Алматы (UTC+6)"),
    ("Asia/Tashkent", "Ташкент (UTC+5)"),
    ("Asia/Baku", "Баку (UTC+4)"),
    ("Asia/Yerevan", "Ереван (UTC+4)"),
    ("Asia/Tbilisi", "Тбилиси (UTC+4)"),
    ("Asia/Ho_Chi_Minh", "Хошимин/Бангкок (UTC+7)"),
    ("Europe/Berlin", "Берлин (UTC+1/+2)"),
    ("Europe/London", "Лондон (UTC+0/+1)"),
]

TIMEZONE_MANUAL_OPTION_CODE = "manual"
