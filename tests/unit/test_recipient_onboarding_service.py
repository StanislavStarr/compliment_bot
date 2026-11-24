from datetime import time as dt_time
from typing import Any
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from app.application.orders.notices import NoticeKind
from app.application.orders.service import OpenOrderExistsError
from app.application.recipient_onboarding.service import (
    RecipientOnboardingError,
    RecipientOnboardingService,
)
from app.domain.orders.enums import InviteStatus, OrderStatus
from app.domain.schedules.enums import ScheduleMode
from app.domain.users.enums import RecipientOnboardingStep, UserRole, UserStatus


def _service() -> tuple[RecipientOnboardingService, AsyncMock, AsyncMock, AsyncMock, AsyncMock]:
    session = AsyncMock()
    service = RecipientOnboardingService(session)
    orders = AsyncMock()
    invites = AsyncMock()
    schedules = AsyncMock()
    order_service = AsyncMock()
    bind: Any = service
    bind.orders = orders
    bind.invites = invites
    bind.schedules = schedules
    bind.order_service = order_service
    return service, session, orders, schedules, order_service


def _recipient() -> MagicMock:
    user = MagicMock()
    user.id = uuid4()
    user.role = None
    user.recipient_step = RecipientOnboardingStep.CONSENT
    user.status = UserStatus.ONBOARDING
    return user


def _order(*, author_id: object | None = None) -> MagicMock:
    order = MagicMock()
    order.id = uuid4()
    order.author_id = author_id or uuid4()
    order.recipient_user_id = None
    order.status = OrderStatus.PENDING
    return order


async def test_accept_binds_recipient_and_does_not_activate() -> None:
    service, session, orders, schedules, _order_service = _service()
    recipient = _recipient()
    order = _order()
    invite = MagicMock()
    invite.status = InviteStatus.PENDING
    orders.get_open_for_recipient.return_value = None

    await service.accept(invite, order, recipient)

    assert invite.status is InviteStatus.ACCEPTED
    assert order.recipient_user_id == recipient.id
    assert order.status is OrderStatus.PENDING
    assert recipient.role is UserRole.RECIPIENT
    assert recipient.recipient_step is RecipientOnboardingStep.TIMEZONE
    assert recipient.status is UserStatus.ONBOARDING
    schedules.upsert.assert_not_awaited()
    session.commit.assert_awaited_once()


async def test_accept_rejects_second_open_order() -> None:
    service, _session, orders, schedules, _order_service = _service()
    recipient = _recipient()
    order = _order()
    other = _order()
    other.id = uuid4()
    orders.get_open_for_recipient.return_value = other

    with pytest.raises(OpenOrderExistsError):
        await service.accept(MagicMock(), order, recipient)

    schedules.upsert.assert_not_awaited()


async def test_accept_rejects_author_as_recipient() -> None:
    service, _session, _orders, schedules, _order_service = _service()
    recipient = _recipient()
    order = _order(author_id=recipient.id)

    with pytest.raises(RecipientOnboardingError):
        await service.accept(MagicMock(), order, recipient)

    schedules.upsert.assert_not_awaited()


async def test_decline_cancels_without_schedule() -> None:
    service, _session, _orders, _schedules, order_service = _service()
    order = _order()
    notice = MagicMock()
    order_service.cancel.return_value = notice

    result = await service.decline(order)

    assert result is notice
    order_service.cancel.assert_awaited_once_with(order, initiated_by=NoticeKind.RECIPIENT_DECLINED)


async def test_complete_requires_schedule() -> None:
    service, _session, _orders, schedules, _order_service = _service()
    recipient = _recipient()
    order = _order()
    order.recipient_user_id = recipient.id
    schedules.get_by_user_id.return_value = None

    with pytest.raises(RecipientOnboardingError):
        await service.complete(recipient, order)

    assert order.status is OrderStatus.PENDING


async def test_finalize_schedule_writes_slot_for_bound_recipient() -> None:
    service, session, _orders, schedules, _order_service = _service()
    recipient = _recipient()
    order = _order()
    order.recipient_user_id = recipient.id

    await service.finalize_schedule(
        recipient, order, "Europe/Moscow", ScheduleMode.EXACT, exact_local_time=dt_time(9, 0)
    )

    schedules.upsert.assert_awaited_once()
    kwargs = schedules.upsert.await_args.kwargs
    assert kwargs["user_id"] == recipient.id
    assert kwargs["order_id"] == order.id
    assert kwargs["timezone_name"] == "Europe/Moscow"
    session.commit.assert_awaited()


async def test_finalize_schedule_rejects_unbound_recipient() -> None:
    service, _session, _orders, schedules, _order_service = _service()
    recipient = _recipient()
    order = _order()

    with pytest.raises(RecipientOnboardingError):
        await service.finalize_schedule(
            recipient, order, "Europe/Moscow", ScheduleMode.EXACT, exact_local_time=dt_time(9, 0)
        )

    schedules.upsert.assert_not_awaited()


async def test_complete_activates_when_schedule_exists() -> None:
    service, session, _orders, schedules, _order_service = _service()
    recipient = _recipient()
    order = _order()
    order.recipient_user_id = recipient.id
    schedules.get_by_user_id.return_value = MagicMock()

    await service.complete(recipient, order)

    assert order.status is OrderStatus.ACTIVE
    assert recipient.status is UserStatus.ACTIVE
    assert recipient.recipient_step is RecipientOnboardingStep.DONE
    session.commit.assert_awaited_once()
