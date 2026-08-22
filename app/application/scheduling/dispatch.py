from datetime import datetime, timedelta

from app.domain.schedules.enums import MISSED_DELIVERY_THRESHOLD_HOURS


def is_missed_beyond_threshold(planned_at_utc: datetime, now_utc: datetime) -> bool:
    """Раздел 17: опоздание больше двух часов — доставку не отправляем,
    слот дня пропускаем и считаем следующий запуск."""
    return now_utc - planned_at_utc > timedelta(hours=MISSED_DELIVERY_THRESHOLD_HOURS)
