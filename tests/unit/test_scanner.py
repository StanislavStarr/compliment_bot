from datetime import UTC, datetime, time
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

from app.application.scheduling.scanner import collect_due_delivery_ids
from app.domain.schedules.enums import ScheduleMode


def _schedule(*, overdue: bool) -> MagicMock:
    schedule = MagicMock()
    schedule.id = uuid4()
    schedule.user_id = uuid4()
    schedule.timezone_name = "UTC"
    schedule.mode = ScheduleMode.EXACT
    schedule.exact_local_time = time(10, 0)
    schedule.period = None
    if overdue:
        schedule.next_run_at_utc = datetime(2026, 8, 20, 0, 0, tzinfo=UTC)
    else:
        schedule.next_run_at_utc = datetime(2026, 8, 22, 10, 0, tzinfo=UTC)
    return schedule


async def test_due_schedule_creates_delivery_once() -> None:
    session = AsyncMock()
    schedule = _schedule(overdue=False)
    delivery = MagicMock()
    delivery.id = uuid4()

    schedules = AsyncMock()
    schedules.lock_due_batch.return_value = [schedule]
    deliveries = AsyncMock()
    deliveries.get_or_create.return_value = (delivery, True)

    now = datetime(2026, 8, 22, 10, 1, tzinfo=UTC)
    with (
        patch("app.application.scheduling.scanner.ScheduleRepository", return_value=schedules),
        patch("app.application.scheduling.scanner.DeliveryRepository", return_value=deliveries),
    ):
        created = await collect_due_delivery_ids(session, now)

    assert created == [str(delivery.id)]
    deliveries.get_or_create.assert_awaited_once()
    schedules.mark_sent.assert_not_awaited()


async def test_existing_delivery_is_not_enqueued_again() -> None:
    session = AsyncMock()
    schedule = _schedule(overdue=False)
    delivery = MagicMock()
    delivery.id = uuid4()

    schedules = AsyncMock()
    schedules.lock_due_batch.return_value = [schedule]
    deliveries = AsyncMock()
    deliveries.get_or_create.return_value = (delivery, False)

    now = datetime(2026, 8, 22, 10, 1, tzinfo=UTC)
    with (
        patch("app.application.scheduling.scanner.ScheduleRepository", return_value=schedules),
        patch("app.application.scheduling.scanner.DeliveryRepository", return_value=deliveries),
    ):
        created = await collect_due_delivery_ids(session, now)

    assert created == []


async def test_missed_beyond_threshold_skips_slot_without_delivery() -> None:
    session = AsyncMock()
    schedule = _schedule(overdue=True)
    schedules = AsyncMock()
    schedules.lock_due_batch.return_value = [schedule]
    deliveries = AsyncMock()

    now = datetime(2026, 8, 22, 10, 0, tzinfo=UTC)
    with (
        patch("app.application.scheduling.scanner.ScheduleRepository", return_value=schedules),
        patch("app.application.scheduling.scanner.DeliveryRepository", return_value=deliveries),
    ):
        created = await collect_due_delivery_ids(session, now)

    assert created == []
    deliveries.get_or_create.assert_not_awaited()
    schedules.mark_sent.assert_awaited_once()
