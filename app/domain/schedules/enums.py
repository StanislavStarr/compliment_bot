from enum import StrEnum


class ScheduleMode(StrEnum):
    EXACT = "exact"
    PERIOD = "period"


class Period(StrEnum):
    MORNING = "morning"  # 07:00-11:00
    DAY = "day"  # 12:00-17:00
    EVENING = "evening"  # 18:00-21:00


PERIOD_WINDOWS: dict[Period, tuple[int, int]] = {
    Period.MORNING: (7, 11),
    Period.DAY: (12, 17),
    Period.EVENING: (18, 21),
}


class DeliveryStatus(StrEnum):
    QUEUED = "queued"
    GENERATING = "generating"
    READY = "ready"
    SENDING = "sending"
    SENT = "sent"
    FAILED = "failed"
    EXPIRED = "expired"


MISSED_DELIVERY_THRESHOLD_HOURS = 2
