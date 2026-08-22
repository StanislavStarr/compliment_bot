from datetime import UTC, datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.application.scheduling.calculator import compute_next_run
from app.domain.users.enums import UserStatus
from app.infrastructure.db.models.users import User
from app.infrastructure.db.repositories.schedules import ScheduleRepository
from app.infrastructure.db.repositories.users import UserRepository


class SettingsService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self.users = UserRepository(session)
        self.schedules = ScheduleRepository(session)

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

    async def delete_account(self, user: User) -> None:
        await self.users.delete(user)
        await self._session.commit()
