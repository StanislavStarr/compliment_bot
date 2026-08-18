import asyncio
from datetime import UTC, datetime
from zoneinfo import ZoneInfo

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
    каждого пользователя. `next_run_at_utc` здесь не продвигается — это
    делает delivery-таск после завершения доставки, поэтому даже если
    несколько тиков подряд увидят одно и то же due-расписание, вторая
    попытка создать `Delivery` за тот же локальный день упадёт на unique
    constraint и просто не поставит задачу в очередь повторно."""
    now_utc = datetime.now(UTC)
    to_enqueue: list[str] = []

    session_factory = get_celery_session_factory()
    async with session_factory() as session:
        schedule_repo = ScheduleRepository(session)
        delivery_repo = DeliveryRepository(session)

        due_schedules = await schedule_repo.lock_due_batch(now_utc, limit=DUE_SCAN_BATCH_SIZE)
        for schedule in due_schedules:
            local_date = now_utc.astimezone(ZoneInfo(schedule.timezone_name)).date()
            idempotency_key = f"{schedule.user_id}:{local_date.isoformat()}"

            delivery, created = await delivery_repo.get_or_create(
                user_id=schedule.user_id,
                schedule_id=schedule.id,
                local_delivery_date=local_date,
                planned_at_utc=schedule.next_run_at_utc,
                idempotency_key=idempotency_key,
            )
            if created:
                to_enqueue.append(str(delivery.id))

        await session.commit()

    logger.info("due_schedules_dispatched", found=len(due_schedules), created=len(to_enqueue))

    for delivery_id in to_enqueue:
        deliver_message_task.delay(delivery_id)


celery_app.conf.beat_schedule = {
    "dispatch-due-schedules-every-minute": {
        "task": "tasks.dispatch_due_schedules",
        "schedule": 60.0,
    },
}
