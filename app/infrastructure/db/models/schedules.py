import uuid
from datetime import date, datetime, time

from sqlalchemy import Boolean, Date, DateTime, Enum, ForeignKey, Integer, String, Time
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.domain.schedules.enums import Period, ScheduleMode
from app.infrastructure.db.base import Base, TimestampMixin, UUIDPkMixin


class Schedule(Base, UUIDPkMixin, TimestampMixin):
    __tablename__ = "schedules"

    user_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        unique=True,
        nullable=False,
    )

    mode: Mapped[ScheduleMode] = mapped_column(
        Enum(ScheduleMode, name="schedule_mode"), nullable=False
    )
    exact_local_time: Mapped[time | None] = mapped_column(Time)
    period: Mapped[Period | None] = mapped_column(Enum(Period, name="schedule_period"))

    timezone_name: Mapped[str] = mapped_column(String(64), nullable=False)
    fixed_utc_offset_minutes: Mapped[int | None] = mapped_column(Integer)

    next_run_at_utc: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    last_sent_local_date: Mapped[date | None] = mapped_column(Date)

    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    paused_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


__all__ = ["Schedule"]
