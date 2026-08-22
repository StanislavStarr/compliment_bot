import uuid
from datetime import UTC, datetime
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

from app.application.settings.service import SettingsService
from app.domain.schedules.enums import Period, ScheduleMode
from app.domain.users.enums import UserStatus


def _service() -> tuple[SettingsService, AsyncMock, AsyncMock, AsyncMock, MagicMock]:
    session = AsyncMock()
    service = SettingsService(session)
    users = AsyncMock()
    schedules = AsyncMock()
    bind: Any = service
    bind.users = users
    bind.schedules = schedules
    user = MagicMock()
    user.id = uuid.uuid4()
    user.status = UserStatus.ACTIVE
    return service, session, users, schedules, user


def _schedule() -> MagicMock:
    schedule = MagicMock()
    schedule.timezone_name = "Asia/Krasnoyarsk"
    schedule.mode = ScheduleMode.PERIOD
    schedule.exact_local_time = None
    schedule.period = Period.MORNING
    return schedule


async def test_pause_marks_user_and_schedule() -> None:
    service, session, _users, schedules, user = _service()
    schedule = _schedule()
    schedules.get_by_user_id.return_value = schedule

    await service.pause(user)

    assert user.status is UserStatus.PAUSED
    schedules.pause.assert_awaited_once_with(schedule)
    session.commit.assert_awaited_once()


async def test_resume_recomputes_next_run() -> None:
    service, session, _users, schedules, user = _service()
    user.status = UserStatus.PAUSED
    schedule = _schedule()
    schedules.get_by_user_id.return_value = schedule
    next_run = datetime(2026, 8, 23, 3, 6, tzinfo=UTC)

    with patch(
        "app.application.settings.service.compute_next_run", return_value=next_run
    ) as compute:
        await service.resume(user)

    assert user.status is UserStatus.ACTIVE
    compute.assert_called_once()
    schedules.resume.assert_awaited_once_with(schedule, next_run)
    session.commit.assert_awaited_once()


async def test_delete_account_removes_user() -> None:
    service, session, users, _schedules, user = _service()

    await service.delete_account(user)

    users.delete.assert_awaited_once_with(user)
    session.commit.assert_awaited_once()


async def test_settings_keyboard_shows_generate_only_for_admin() -> None:
    from app.infrastructure.telegram.keyboards.settings import settings_keyboard

    admin_data = [
        button.callback_data
        for row in settings_keyboard(paused=False, is_admin=True).inline_keyboard
        for button in row
    ]
    user_data = [
        button.callback_data
        for row in settings_keyboard(paused=False, is_admin=False).inline_keyboard
        for button in row
    ]
    assert "settings:generate" in admin_data
    assert "settings:generate" not in user_data
