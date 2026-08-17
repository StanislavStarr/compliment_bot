import random
from datetime import UTC, datetime, time
from zoneinfo import ZoneInfo

from app.application.scheduling.calculator import (
    compute_next_run_for_exact_time,
    compute_next_run_for_period,
)
from app.domain.schedules.enums import Period

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
