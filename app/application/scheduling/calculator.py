import random
from datetime import UTC, date, datetime, time, timedelta
from zoneinfo import ZoneInfo

from app.domain.schedules.enums import PERIOD_WINDOWS, Period, ScheduleMode


def compute_next_run_for_exact_time(
    now_utc: datetime, timezone_name: str, exact_local_time: time
) -> datetime:
    """Следующее наступление точного локального времени, строго в будущем
    относительно `now_utc`. `now_utc` передаётся явно — как и `rand` в
    period-версии — чтобы тесты были детерминированными (без реального часов)."""
    tz = ZoneInfo(timezone_name)
    now_local = now_utc.astimezone(tz)

    candidate_local = datetime.combine(now_local.date(), exact_local_time, tzinfo=tz)
    if candidate_local <= now_local:
        candidate_local = datetime.combine(
            now_local.date() + timedelta(days=1), exact_local_time, tzinfo=tz
        )

    return candidate_local.astimezone(UTC)


def compute_next_run_for_period(
    now_utc: datetime,
    timezone_name: str,
    period: Period,
    rand: random.Random,
) -> datetime:
    """Случайный момент внутри окна периода на следующий подходящий локальный
    день, строго в будущем относительно `now_utc`."""
    tz = ZoneInfo(timezone_name)
    now_local = now_utc.astimezone(tz)

    candidate_local = _random_moment_in_window(now_local.date(), period, tz, rand)
    if candidate_local <= now_local:
        candidate_local = _random_moment_in_window(
            now_local.date() + timedelta(days=1), period, tz, rand
        )

    return candidate_local.astimezone(UTC)


def compute_next_run(
    now_utc: datetime,
    timezone_name: str,
    mode: ScheduleMode,
    exact_local_time: time | None,
    period: Period | None,
    rand: random.Random | None = None,
) -> datetime:
    """Общая точка входа для обоих режимов — использует и онбординг
    (`finalize_schedule`), и delivery-таск после завершения доставки, чтобы
    ветвление exact/period не дублировалось в двух местах."""
    if mode is ScheduleMode.EXACT:
        if exact_local_time is None:
            raise ValueError("exact_local_time обязателен для режима EXACT")
        return compute_next_run_for_exact_time(now_utc, timezone_name, exact_local_time)

    if period is None:
        raise ValueError("period обязателен для режима PERIOD")
    return compute_next_run_for_period(now_utc, timezone_name, period, rand or random.Random())


def _random_moment_in_window(
    local_date: date, period: Period, tz: ZoneInfo, rand: random.Random
) -> datetime:
    start_hour, end_hour = PERIOD_WINDOWS[period]
    window_start = datetime.combine(local_date, time(hour=start_hour), tzinfo=tz)
    window_end = datetime.combine(local_date, time(hour=end_hour), tzinfo=tz)
    total_seconds = int((window_end - window_start).total_seconds())
    offset_seconds = rand.randint(0, total_seconds)
    return window_start + timedelta(seconds=offset_seconds)
