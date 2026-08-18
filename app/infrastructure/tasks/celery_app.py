from celery import Celery

from app.config import get_settings

settings = get_settings()

celery_app = Celery(
    "compliment_bot",
    broker=settings.celery_broker_url,
    backend=settings.celery_result_backend,
    include=[
        "app.infrastructure.tasks.delivery",
        "app.infrastructure.tasks.scheduler",
    ],
)

celery_app.conf.update(
    task_default_queue="compliment_bot",
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
)
