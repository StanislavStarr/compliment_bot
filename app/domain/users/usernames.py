def normalize_telegram_username(raw: str | None) -> str | None:
    """Нижний регистр, без `@`. Пустая строка → None."""
    if raw is None:
        return None
    value = raw.strip().lstrip("@").lower()
    return value or None
