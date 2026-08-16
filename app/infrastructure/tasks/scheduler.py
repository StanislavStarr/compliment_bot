from app.infrastructure.logging.setup import get_logger
from app.infrastructure.tasks.celery_app import celery_app

logger = get_logger(__name__)


@celery_app.task(name="tasks.heartbeat")  # type: ignore[untyped-decorator]
def heartbeat() -> None:
    """Проверка связки worker + beat + Redis.
    Будет заменена на dispatch_due_schedules в Этапе 5.
    """
    logger.info("beat_heartbeat")


celery_app.conf.beat_schedule = {
    "heartbeat-every-minute": {
        "task": "tasks.heartbeat",
        "schedule": 60.0,
    },
}
