import asyncio
from datetime import UTC, datetime

from app.application.scheduling.scanner import collect_due_delivery_ids
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
    каждого пользователя."""
    now_utc = datetime.now(UTC)
    session_factory = get_celery_session_factory()
    async with session_factory() as session:
        to_enqueue = await collect_due_delivery_ids(session, now_utc)
        await session.commit()

    logger.info("due_schedules_dispatched", created=len(to_enqueue))

    for delivery_id in to_enqueue:
        deliver_message_task.delay(delivery_id)


celery_app.conf.beat_schedule = {
    "dispatch-due-schedules-every-minute": {
        "task": "tasks.dispatch_due_schedules",
        "schedule": 60.0,
    },
}
