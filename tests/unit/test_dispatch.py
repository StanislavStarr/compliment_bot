from datetime import UTC, datetime, timedelta

from app.application.scheduling.dispatch import is_missed_beyond_threshold


def test_within_two_hours_is_not_missed() -> None:
    planned = datetime(2026, 8, 20, 2, 5, tzinfo=UTC)
    now = planned + timedelta(hours=2)

    assert is_missed_beyond_threshold(planned, now) is False


def test_just_over_two_hours_is_missed() -> None:
    planned = datetime(2026, 8, 20, 2, 5, tzinfo=UTC)
    now = planned + timedelta(hours=2, seconds=1)

    assert is_missed_beyond_threshold(planned, now) is True
