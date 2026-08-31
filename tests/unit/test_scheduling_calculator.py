import random
from datetime import UTC, date, datetime, time, timedelta
from zoneinfo import ZoneInfo

import pytest

from app.application.scheduling.calculator import (
    compute_next_run,
    compute_next_run_after,
    compute_next_run_for_exact_time,
    compute_next_run_for_period,
)
from app.domain.schedules.enums import Period, ScheduleMode

HO_CHI_MINH = ZoneInfo("Asia/Ho_Chi_Minh")


def test_exact_time_today_if_still_ahead() -> None:
    # 10:00 UTC = 17:00 в Asia/Ho_Chi_Minh (UTC+7); просим 18:00 локально сегодня.
    now_utc = datetime(2026, 1, 5, 10, 0, tzinfo=UTC)

    result = compute_next_run_for_exact_time(now_utc, "Asia/Ho_Chi_Minh", time(18, 0))

    assert result == datetime(2026, 1, 5, 11, 0, tzinfo=UTC)


def test_exact_time_rolls_over_to_tomorrow_when_already_passed() -> None:
    # 13:00 UTC = 20:00 в Asia/Ho_Chi_Minh; просим 18:00 — время уже прошло сегодня.
    now_utc = datetime(2026, 1, 5, 13, 0, tzinfo=UTC)

    result = compute_next_run_for_exact_time(now_utc, "Asia/Ho_Chi_Minh", time(18, 0))

    assert result == datetime(2026, 1, 6, 11, 0, tzinfo=UTC)


def test_period_result_falls_within_window_and_is_in_future() -> None:
    now_utc = datetime(2026, 1, 5, 0, 0, tzinfo=UTC)
    rand = random.Random(42)

    result = compute_next_run_for_period(now_utc, "Asia/Ho_Chi_Minh", Period.MORNING, rand)
    local = result.astimezone(HO_CHI_MINH)

    assert result > now_utc
    assert 7 <= local.hour < 11


def test_period_rolls_over_when_window_already_passed_today() -> None:
    # 12:00 UTC = 19:00 локально — окно "morning" (07:00-11:00) уже прошло.
    now_utc = datetime(2026, 1, 5, 12, 0, tzinfo=UTC)
    rand = random.Random(1)

    result = compute_next_run_for_period(now_utc, "Asia/Ho_Chi_Minh", Period.MORNING, rand)
    local = result.astimezone(HO_CHI_MINH)

    assert local.date().isoformat() == "2026-01-06"
    assert 7 <= local.hour < 11


def test_compute_next_run_dispatches_to_exact_time() -> None:
    now_utc = datetime(2026, 1, 5, 10, 0, tzinfo=UTC)

    result = compute_next_run(now_utc, "Asia/Ho_Chi_Minh", ScheduleMode.EXACT, time(18, 0), None)

    assert result == compute_next_run_for_exact_time(now_utc, "Asia/Ho_Chi_Minh", time(18, 0))


def test_compute_next_run_dispatches_to_period() -> None:
    now_utc = datetime(2026, 1, 5, 0, 0, tzinfo=UTC)

    result = compute_next_run(
        now_utc, "Asia/Ho_Chi_Minh", ScheduleMode.PERIOD, None, Period.MORNING, random.Random(42)
    )
    local = result.astimezone(HO_CHI_MINH)

    assert 7 <= local.hour < 11


def test_compute_next_run_requires_exact_local_time_for_exact_mode() -> None:
    now_utc = datetime(2026, 1, 5, 10, 0, tzinfo=UTC)

    with pytest.raises(ValueError, match="exact_local_time"):
        compute_next_run(now_utc, "Asia/Ho_Chi_Minh", ScheduleMode.EXACT, None, None)


def test_compute_next_run_requires_period_for_period_mode() -> None:
    now_utc = datetime(2026, 1, 5, 10, 0, tzinfo=UTC)

    with pytest.raises(ValueError, match="period"):
        compute_next_run(now_utc, "Asia/Ho_Chi_Minh", ScheduleMode.PERIOD, None, None)


def test_timezone_converts_local_exact_time_to_utc() -> None:
    now_utc = datetime(2026, 1, 5, 1, 0, tzinfo=UTC)
    krasnoyarsk = ZoneInfo("Asia/Krasnoyarsk")

    result = compute_next_run_for_exact_time(now_utc, "Asia/Krasnoyarsk", time(10, 6))
    local = result.astimezone(krasnoyarsk)

    assert local.hour == 10
    assert local.minute == 6
    assert result.tzinfo is UTC or result.utcoffset() == timedelta(0)


def test_exact_time_crosses_utc_day_boundary() -> None:
    now_utc = datetime(2026, 1, 5, 23, 30, tzinfo=UTC)

    result = compute_next_run_for_exact_time(now_utc, "Asia/Ho_Chi_Minh", time(7, 0))
    local = result.astimezone(HO_CHI_MINH)

    assert local.date() == date(2026, 1, 6)
    assert local.hour == 7


def test_compute_next_run_after_moves_to_next_local_day() -> None:
    # 10:00 UTC = 17:00 +7; 18:00 локально ещё сегодня, но слот дня уже занят.
    now_utc = datetime(2026, 1, 5, 10, 0, tzinfo=UTC)
    sent_on = date(2026, 1, 5)

    result = compute_next_run_after(
        sent_on, now_utc, "Asia/Ho_Chi_Minh", ScheduleMode.EXACT, time(18, 0), None
    )
    local = result.astimezone(HO_CHI_MINH)

    assert local.date() == date(2026, 1, 6)
    assert local.hour == 18
