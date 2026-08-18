from app.domain.schedules.constants import DELIVERY_MAX_RETRIES, DELIVERY_RETRY_DELAYS_SECONDS
from app.infrastructure.tasks.delivery import (
    PermanentDeliveryError,
    TransientDeliveryError,
    _retry_countdown,
)


def test_retry_countdown_follows_1_5_15_minutes_schedule() -> None:
    assert _retry_countdown(0) == 60
    assert _retry_countdown(1) == 300
    assert _retry_countdown(2) == 900


def test_retry_countdown_caps_at_last_delay_beyond_max_retries() -> None:
    assert _retry_countdown(10) == DELIVERY_RETRY_DELAYS_SECONDS[-1]


def test_delivery_max_retries_matches_delay_schedule_length() -> None:
    assert DELIVERY_MAX_RETRIES == len(DELIVERY_RETRY_DELAYS_SECONDS) == 3


def test_transient_delivery_error_carries_retry_after() -> None:
    error = TransientDeliveryError("telegram_retry_after: ...", retry_after=42)
    assert error.retry_after == 42


def test_permanent_delivery_error_carries_error_code() -> None:
    error = PermanentDeliveryError("telegram_forbidden")
    assert error.error_code == "telegram_forbidden"
