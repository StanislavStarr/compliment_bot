import uuid
from datetime import UTC, date, datetime, time

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.schedules.enums import Period, ScheduleMode
from app.infrastructure.db.models.schedules import Schedule


class ScheduleRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_user_id(self, user_id: uuid.UUID) -> Schedule | None:
        result = await self._session.execute(select(Schedule).where(Schedule.user_id == user_id))
        return result.scalar_one_or_none()

    async def upsert(
        self,
        user_id: uuid.UUID,
        mode: ScheduleMode,
        timezone_name: str,
        next_run_at_utc: datetime,
        exact_local_time: time | None = None,
        period: Period | None = None,
    ) -> Schedule:
        schedule = await self.get_by_user_id(user_id)
        if schedule is None:
            schedule = Schedule(user_id=user_id)
            self._session.add(schedule)

        schedule.mode = mode
        schedule.timezone_name = timezone_name
        schedule.exact_local_time = exact_local_time
        schedule.period = period
        schedule.next_run_at_utc = next_run_at_utc
        schedule.is_active = True
        schedule.paused_at = None

        await self._session.flush()
        return schedule

    async def mark_sent(
        self, schedule: Schedule, local_date: date, next_run_at_utc: datetime
    ) -> None:
        schedule.last_sent_local_date = local_date
        schedule.next_run_at_utc = next_run_at_utc
        await self._session.flush()

    async def lock_due_batch(self, now_utc: datetime, limit: int) -> list[Schedule]:
        """`FOR UPDATE SKIP LOCKED` — несколько worker-процессов (при
        масштабировании) не возьмут одно и то же расписание одновременно.
        Не продвигает `next_run_at_utc` — это делает delivery-таск после
        завершения доставки (раздел 17 плана)."""
        result = await self._session.execute(
            select(Schedule)
            .where(Schedule.is_active.is_(True), Schedule.next_run_at_utc <= now_utc)
            .order_by(Schedule.next_run_at_utc)
            .limit(limit)
            .with_for_update(skip_locked=True)
        )
        return list(result.scalars().all())

    async def pause(self, schedule: Schedule) -> None:
        schedule.is_active = False
        schedule.paused_at = datetime.now(UTC)
        await self._session.flush()
