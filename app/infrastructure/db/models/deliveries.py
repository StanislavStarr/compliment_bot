import uuid
from datetime import date, datetime

from sqlalchemy import Date, DateTime, Enum, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.domain.schedules.enums import DeliveryStatus
from app.infrastructure.db.base import Base, TimestampMixin, UUIDPkMixin


class Delivery(Base, UUIDPkMixin, TimestampMixin):
    """Уникальность (user_id, local_delivery_date) — идемпотентность плановой
    доставки. Отдельная колонка `delivery_kind` из документа не заводится:
    в этом проходе MVP есть только плановые доставки, ручная генерация вынесена
    за скоуп Gift Release."""

    __tablename__ = "deliveries"
    __table_args__ = (
        UniqueConstraint("user_id", "local_delivery_date", name="uq_deliveries_user_local_date"),
    )

    user_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    schedule_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("schedules.id", ondelete="CASCADE"), nullable=False
    )

    local_delivery_date: Mapped[date] = mapped_column(Date, nullable=False)
    planned_at_utc: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    status: Mapped[DeliveryStatus] = mapped_column(
        Enum(DeliveryStatus, name="delivery_status"), nullable=False, default=DeliveryStatus.QUEUED
    )
    idempotency_key: Mapped[str] = mapped_column(String(128), unique=True, nullable=False)
    attempt_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    last_error_code: Mapped[str | None] = mapped_column(String(64))
    sent_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


__all__ = ["Delivery"]
