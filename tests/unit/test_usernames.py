from app.domain.users.usernames import normalize_telegram_username


def test_normalize_strips_at_and_lowercases() -> None:
    assert normalize_telegram_username("@Ivan_Petrov") == "ivan_petrov"


def test_normalize_empty_is_none() -> None:
    assert normalize_telegram_username("   ") is None
    assert normalize_telegram_username(None) is None
