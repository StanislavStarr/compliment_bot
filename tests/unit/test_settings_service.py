import uuid
from datetime import UTC, datetime
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

from app.application.orders.notices import NoticeKind
from app.application.settings.service import SettingsService
from app.domain.schedules.enums import Period, ScheduleMode
from app.domain.users.enums import UserRole, UserStatus


def _service() -> tuple[SettingsService, AsyncMock, AsyncMock, AsyncMock, MagicMock, AsyncMock]:
    session = AsyncMock()
    service = SettingsService(session)
    users = AsyncMock()
    schedules = AsyncMock()
    orders = AsyncMock()
    orders.get_open_for_author.return_value = None
    orders.get_open_for_recipient.return_value = None
    bind: Any = service
    bind.users = users
    bind.schedules = schedules
    bind.orders = orders
    user = MagicMock()
    user.id = uuid.uuid4()
    user.status = UserStatus.ACTIVE
    user.role = UserRole.AUTHOR
    return service, session, users, schedules, user, orders


def _schedule() -> MagicMock:
    schedule = MagicMock()
    schedule.timezone_name = "Asia/Krasnoyarsk"
    schedule.mode = ScheduleMode.PERIOD
    schedule.exact_local_time = None
    schedule.period = Period.MORNING
    return schedule


async def test_pause_marks_user_and_schedule() -> None:
    service, session, _users, schedules, user, _orders = _service()
    schedule = _schedule()
    schedules.get_by_user_id.return_value = schedule

    await service.pause(user)

    assert user.status is UserStatus.PAUSED
    schedules.pause.assert_awaited_once_with(schedule)
    session.commit.assert_awaited_once()


async def test_resume_recomputes_next_run() -> None:
    service, session, _users, schedules, user, _orders = _service()
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
    service, session, users, _schedules, user, _orders = _service()

    result = await service.delete_account(user)

    assert result is None
    users.delete.assert_awaited_once_with(user)
    session.commit.assert_awaited_once()


async def test_delete_account_cancels_author_order() -> None:
    service, session, users, _schedules, user, orders = _service()
    order = MagicMock()
    notice = MagicMock()
    orders.get_open_for_author.return_value = order
    orders.cancel.return_value = notice

    result = await service.delete_account(user)

    orders.cancel.assert_awaited_once_with(order, initiated_by=NoticeKind.AUTHOR_CANCELLED)
    users.delete.assert_awaited_once_with(user)
    assert result is notice
    session.commit.assert_awaited()


async def test_delete_account_cancels_recipient_order() -> None:
    service, _session, users, _schedules, user, orders = _service()
    user.role = UserRole.RECIPIENT
    order = MagicMock()
    notice = MagicMock()
    orders.get_open_for_recipient.return_value = order
    orders.cancel.return_value = notice

    result = await service.delete_account(user)

    orders.cancel.assert_awaited_once_with(order, initiated_by=NoticeKind.RECIPIENT_STOPPED)
    users.delete.assert_awaited_once_with(user)
    assert result is notice


async def test_recipient_keyboard_shows_generate_only_for_admin() -> None:
    from app.infrastructure.telegram.keyboards.settings import recipient_home_keyboard

    admin_data = [
        button.callback_data
        for row in recipient_home_keyboard(paused=False, is_admin=True).inline_keyboard
        for button in row
    ]
    user_data = [
        button.callback_data
        for row in recipient_home_keyboard(paused=False, is_admin=False).inline_keyboard
        for button in row
    ]
    assert "settings:generate" in admin_data
    assert "settings:generate" not in user_data
    assert "order:stop" in user_data
    assert "settings:slot" in user_data


async def test_author_keyboard_has_cancel() -> None:
    from app.infrastructure.telegram.keyboards.settings import author_home_keyboard

    data = [
        button.callback_data
        for row in author_home_keyboard(cancellable=True).inline_keyboard
        for button in row
    ]
    assert "order:cancel" in data
    assert "settings:pause" not in data
