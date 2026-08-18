import uuid
from datetime import UTC, date, datetime

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.schedules.enums import DeliveryStatus
from app.infrastructure.db.models.deliveries import Delivery


class DeliveryRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_user_and_date(
        self, user_id: uuid.UUID, local_delivery_date: date
    ) -> Delivery | None:
        result = await self._session.execute(
            select(Delivery).where(
                Delivery.user_id == user_id,
                Delivery.local_delivery_date == local_delivery_date,
            )
        )
        return result.scalar_one_or_none()

    async def get_for_update(self, delivery_id: uuid.UUID) -> Delivery | None:
        result = await self._session.execute(
            select(Delivery).where(Delivery.id == delivery_id).with_for_update()
        )
        return result.scalar_one_or_none()

    async def get_or_create(
        self,
        *,
        user_id: uuid.UUID,
        schedule_id: uuid.UUID,
        local_delivery_date: date,
        planned_at_utc: datetime,
        idempotency_key: str,
    ) -> tuple[Delivery, bool]:
        """Возвращает `(delivery, created)`. Идемпотентность держится на
        unique(user_id, local_delivery_date) в БД: SAVEPOINT ловит гонку,
        если два процесса scanner'а попытаются создать доставку одновременно
        (в MVP один Beat, но конструкция остаётся корректной при масштабировании)."""
        existing = await self.get_by_user_and_date(user_id, local_delivery_date)
        if existing is not None:
            return existing, False

        try:
            async with self._session.begin_nested():
                delivery = Delivery(
                    user_id=user_id,
                    schedule_id=schedule_id,
                    local_delivery_date=local_delivery_date,
                    planned_at_utc=planned_at_utc,
                    idempotency_key=idempotency_key,
                    status=DeliveryStatus.QUEUED,
                )
                self._session.add(delivery)
                await self._session.flush()
        except IntegrityError:
            existing = await self.get_by_user_and_date(user_id, local_delivery_date)
            if existing is None:
                raise
            return existing, False

        return delivery, True

    async def record_attempt(self, delivery: Delivery, error_code: str | None = None) -> None:
        delivery.attempt_count += 1
        if error_code:
            delivery.last_error_code = error_code
        await self._session.flush()

    async def mark_generating(self, delivery: Delivery) -> None:
        delivery.status = DeliveryStatus.GENERATING
        await self._session.flush()

    async def mark_ready(self, delivery: Delivery) -> None:
        delivery.status = DeliveryStatus.READY
        await self._session.flush()

    async def mark_sending(self, delivery: Delivery) -> None:
        delivery.status = DeliveryStatus.SENDING
        await self._session.flush()

    async def mark_sent(self, delivery: Delivery) -> None:
        delivery.status = DeliveryStatus.SENT
        delivery.sent_at = datetime.now(UTC)
        await self._session.flush()

    async def mark_failed(self, delivery: Delivery, error_code: str) -> None:
        delivery.status = DeliveryStatus.FAILED
        delivery.last_error_code = error_code
        await self._session.flush()

    async def mark_expired(self, delivery: Delivery) -> None:
        delivery.status = DeliveryStatus.EXPIRED
        await self._session.flush()
