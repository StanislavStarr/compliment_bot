from datetime import datetime
from zoneinfo import ZoneInfo

from sqlalchemy.ext.asyncio import AsyncSession

from app.application.scheduling.calculator import compute_next_run_after
from app.application.scheduling.dispatch import (
    delivery_idempotency_key,
    is_missed_beyond_threshold,
)
from app.domain.schedules.constants import DUE_SCAN_BATCH_SIZE
from app.infrastructure.db.repositories.deliveries import DeliveryRepository
from app.infrastructure.db.repositories.schedules import ScheduleRepository


async def collect_due_delivery_ids(
    session: AsyncSession,
    now_utc: datetime,
    batch_size: int = DUE_SCAN_BATCH_SIZE,
) -> list[str]:
    """Сканер due-расписаний. Возвращает id новых Delivery для постановки
    в очередь. `now_utc` передаётся явно — часы injectable для тестов."""
    schedule_repo = ScheduleRepository(session)
    delivery_repo = DeliveryRepository(session)
    to_enqueue: list[str] = []

    due_schedules = await schedule_repo.lock_due_batch(now_utc, limit=batch_size)
    for schedule in due_schedules:
        tz = ZoneInfo(schedule.timezone_name)
        planned_local_date = schedule.next_run_at_utc.astimezone(tz).date()

        if is_missed_beyond_threshold(schedule.next_run_at_utc, now_utc):
            next_run_at_utc = compute_next_run_after(
                planned_local_date,
                now_utc,
                schedule.timezone_name,
                schedule.mode,
                schedule.exact_local_time,
                schedule.period,
            )
            await schedule_repo.mark_sent(schedule, planned_local_date, next_run_at_utc)
            continue

        delivery, created = await delivery_repo.get_or_create(
            user_id=schedule.user_id,
            schedule_id=schedule.id,
            local_delivery_date=planned_local_date,
            planned_at_utc=schedule.next_run_at_utc,
            idempotency_key=delivery_idempotency_key(schedule.user_id, planned_local_date),
        )
        if created:
            to_enqueue.append(str(delivery.id))

    return to_enqueue
