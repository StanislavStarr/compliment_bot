from typing import Any
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from app.application.orders.notices import NoticeKind
from app.application.orders.service import OpenOrderExistsError, OrderService
from app.domain.orders.enums import InviteStatus, OrderStatus
from app.domain.users.enums import UserStatus


def _service() -> tuple[OrderService, AsyncMock, AsyncMock, AsyncMock, AsyncMock, AsyncMock]:
    session = AsyncMock()
    service = OrderService(session)
    orders = AsyncMock()
    invites = AsyncMock()
    users = AsyncMock()
    schedules = AsyncMock()
    bind: Any = service
    bind.orders = orders
    bind.invites = invites
    bind.users = users
    bind.schedules = schedules
    return service, session, orders, invites, users, schedules


def _author() -> MagicMock:
    author = MagicMock()
    author.id = uuid4()
    author.telegram_chat_id = 111
    author.telegram_username = "alice"
    return author


def _order(author_id: object, *, recipient_user_id: object | None = None) -> MagicMock:
    order = MagicMock()
    order.id = uuid4()
    order.author_id = author_id
    order.recipient_user_id = recipient_user_id
    order.recipient_username = "bob"
    order.status = OrderStatus.PENDING
    return order


async def test_create_draft_rejects_second_open_order() -> None:
    service, _session, orders, _invites, _users, _schedules = _service()
    author = _author()
    orders.get_open_for_author.return_value = _order(author.id)

    with pytest.raises(OpenOrderExistsError):
        await service.create_draft(author)

    orders.create_draft.assert_not_awaited()


async def test_cancel_pauses_recipient_schedule_and_notifies() -> None:
    service, session, _orders, invites, users, schedules = _service()
    author = _author()
    recipient = MagicMock()
    recipient.id = uuid4()
    recipient.telegram_chat_id = 222
    recipient.status = UserStatus.ACTIVE
    order = _order(author.id, recipient_user_id=recipient.id)
    invite = MagicMock()
    invite.status = InviteStatus.PENDING
    schedule = MagicMock()
    invites.get_by_order_id.return_value = invite
    schedules.get_by_user_id.return_value = schedule
    users.get_by_id.side_effect = lambda user_id: recipient if user_id == recipient.id else author

    notice = await service.cancel(order, initiated_by=NoticeKind.AUTHOR_CANCELLED)

    assert order.status is OrderStatus.CANCELLED
    assert invite.status is InviteStatus.REVOKED
    schedules.pause.assert_awaited_once_with(schedule)
    assert recipient.status is UserStatus.PAUSED
    assert notice is not None
    assert notice.kind is NoticeKind.AUTHOR_CANCELLED
    assert notice.telegram_chat_id == 222
    session.commit.assert_awaited_once()


async def test_cancel_declined_invite_does_not_touch_schedule() -> None:
    service, session, _orders, invites, users, schedules = _service()
    author = _author()
    order = _order(author.id)
    invite = MagicMock()
    invite.status = InviteStatus.PENDING
    invites.get_by_order_id.return_value = invite
    users.get_by_id.return_value = author

    notice = await service.cancel(order, initiated_by=NoticeKind.RECIPIENT_DECLINED)

    schedules.pause.assert_not_awaited()
    assert order.status is OrderStatus.CANCELLED
    assert invite.status is InviteStatus.REVOKED
    assert notice is not None
    assert notice.kind is NoticeKind.RECIPIENT_DECLINED
    assert notice.telegram_chat_id == author.telegram_chat_id
    session.commit.assert_awaited_once()
