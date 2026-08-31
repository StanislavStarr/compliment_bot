from datetime import UTC, date, datetime, timedelta
from uuid import uuid4

from app.application.scheduling.dispatch import (
    delivery_idempotency_key,
    is_missed_beyond_threshold,
)


def test_within_two_hours_is_not_missed() -> None:
    planned = datetime(2026, 8, 20, 2, 5, tzinfo=UTC)
    now = planned + timedelta(hours=2)

    assert is_missed_beyond_threshold(planned, now) is False


def test_just_over_two_hours_is_missed() -> None:
    planned = datetime(2026, 8, 20, 2, 5, tzinfo=UTC)
    now = planned + timedelta(hours=2, seconds=1)

    assert is_missed_beyond_threshold(planned, now) is True


def test_idempotency_key_is_user_and_local_date() -> None:
    user_id = uuid4()
    local_date = date(2026, 8, 22)

    assert delivery_idempotency_key(user_id, local_date) == f"{user_id}:{local_date.isoformat()}"
