from datetime import UTC, datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.application.orders.notices import CounterpartNotice, NoticeKind
from app.application.orders.service import OrderService
from app.application.scheduling.calculator import compute_next_run
from app.domain.users.enums import UserRole, UserStatus
from app.infrastructure.db.models.users import User
from app.infrastructure.db.repositories.schedules import ScheduleRepository
from app.infrastructure.db.repositories.users import UserRepository


class SettingsService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self.users = UserRepository(session)
        self.schedules = ScheduleRepository(session)
        self.orders = OrderService(session)

    async def pause(self, user: User) -> None:
        user.status = UserStatus.PAUSED
        schedule = await self.schedules.get_by_user_id(user.id)
        if schedule is not None:
            await self.schedules.pause(schedule)
        await self._session.commit()

    async def resume(self, user: User) -> None:
        user.status = UserStatus.ACTIVE
        schedule = await self.schedules.get_by_user_id(user.id)
        if schedule is not None:
            next_run_at_utc = compute_next_run(
                datetime.now(UTC),
                schedule.timezone_name,
                schedule.mode,
                schedule.exact_local_time,
                schedule.period,
            )
            await self.schedules.resume(schedule, next_run_at_utc)
        await self._session.commit()

    async def delete_account(self, user: User) -> CounterpartNotice | None:
        notice = await self._cancel_open_order(user)
        await self.users.delete(user)
        await self._session.commit()
        return notice

    async def _cancel_open_order(self, user: User) -> CounterpartNotice | None:
        if user.role is UserRole.RECIPIENT:
            order = await self.orders.get_open_for_recipient(user)
            if order is None:
                return None
            return await self.orders.cancel(order, initiated_by=NoticeKind.RECIPIENT_STOPPED)
        order = await self.orders.get_open_for_author(user)
        if order is None:
            return None
        return await self.orders.cancel(order, initiated_by=NoticeKind.AUTHOR_CANCELLED)
