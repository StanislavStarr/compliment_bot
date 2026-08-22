import asyncio
from datetime import UTC, datetime
from zoneinfo import ZoneInfo

from app.application.scheduling.calculator import compute_next_run_after
from app.application.scheduling.dispatch import is_missed_beyond_threshold
from app.domain.schedules.constants import DUE_SCAN_BATCH_SIZE
from app.infrastructure.db.repositories.deliveries import DeliveryRepository
from app.infrastructure.db.repositories.schedules import ScheduleRepository
from app.infrastructure.db.session import get_celery_session_factory
from app.infrastructure.logging.setup import get_logger
from app.infrastructure.tasks.celery_app import celery_app
from app.infrastructure.tasks.delivery import deliver_message_task

logger = get_logger(__name__)


@celery_app.task(name="tasks.dispatch_due_schedules")  # type: ignore[untyped-decorator]
def dispatch_due_schedules_task() -> None:
    asyncio.run(_dispatch_due_schedules())


async def _dispatch_due_schedules() -> None:
    """Раз в минуту (Celery Beat). Раздел 17 плана: одна периодическая
    задача сканирует все due расписания, а не создаёт отдельный таймер на
    каждого пользователя.

    Если `next_run_at_utc` просрочен больше чем на 2 часа — доставку не
    создаём (иначе она сразу expired и занимает слот дня), а сразу
    сдвигаем расписание. В пределах порога создаём `Delivery` с датой
    планового запуска; повторный тик упирается в unique
    `(user_id, local_delivery_date)`."""
    now_utc = datetime.now(UTC)
    to_enqueue: list[str] = []
    skipped_missed = 0
    due_schedules = []

    session_factory = get_celery_session_factory()
    async with session_factory() as session:
        schedule_repo = ScheduleRepository(session)
        delivery_repo = DeliveryRepository(session)

        due_schedules = await schedule_repo.lock_due_batch(now_utc, limit=DUE_SCAN_BATCH_SIZE)
        for schedule in due_schedules:
            tz = ZoneInfo(schedule.timezone_name)
            planned_local_date = schedule.next_run_at_utc.astimezone(tz).date()

            # Опоздание > 2 часов: не создаём доставку на «сегодня» со вчерашним
            # planned_at_utc — она сразу станет expired и займёт слот дня.
            # Пропускаем слот и сразу считаем следующий запуск.
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
                skipped_missed += 1
                continue

            idempotency_key = f"{schedule.user_id}:{planned_local_date.isoformat()}"
            delivery, created = await delivery_repo.get_or_create(
                user_id=schedule.user_id,
                schedule_id=schedule.id,
                local_delivery_date=planned_local_date,
                planned_at_utc=schedule.next_run_at_utc,
                idempotency_key=idempotency_key,
            )
            if created:
                to_enqueue.append(str(delivery.id))

        await session.commit()

    logger.info(
        "due_schedules_dispatched",
        found=len(due_schedules),
        created=len(to_enqueue),
        skipped_missed=skipped_missed,
    )

    for delivery_id in to_enqueue:
        deliver_message_task.delay(delivery_id)


celery_app.conf.beat_schedule = {
    "dispatch-due-schedules-every-minute": {
        "task": "tasks.dispatch_due_schedules",
        "schedule": 60.0,
    },
}
