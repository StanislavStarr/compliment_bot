from datetime import date, datetime, timedelta
from uuid import UUID

from app.domain.schedules.enums import MISSED_DELIVERY_THRESHOLD_HOURS


def delivery_idempotency_key(user_id: UUID, local_date: date) -> str:
    """Ключ идемпотентности плановой доставки: один слот на пользователя в день."""
    return f"{user_id}:{local_date.isoformat()}"


def is_missed_beyond_threshold(planned_at_utc: datetime, now_utc: datetime) -> bool:
    """Раздел 17: опоздание больше двух часов — доставку не отправляем,
    слот дня пропускаем и считаем следующий запуск."""
    return now_utc - planned_at_utc > timedelta(hours=MISSED_DELIVERY_THRESHOLD_HOURS)
