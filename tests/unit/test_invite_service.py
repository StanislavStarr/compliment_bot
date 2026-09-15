from typing import Any
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from app.application.invites.service import (
    INVITE_PAYLOAD_PREFIX,
    InviteNotFoundError,
    InviteNotPendingError,
    InviteService,
    UsernameMismatchError,
    UsernameMissingError,
    build_invite_link,
    parse_invite_payload,
)
from app.domain.messages.enums import MessageType
from app.domain.orders.enums import InviteStatus, OrderStatus
from app.domain.users.enums import AddressMode


def _service() -> tuple[InviteService, AsyncMock, AsyncMock, AsyncMock]:
    session = AsyncMock()
    service = InviteService(session)
    invites = AsyncMock()
    orders = AsyncMock()
    bind: Any = service
    bind.invites = invites
    bind.orders = orders
    return service, session, invites, orders


def _order() -> MagicMock:
    order = MagicMock()
    order.id = uuid4()
    order.status = OrderStatus.PENDING
    order.recipient_username = "ivan_petrov"
    order.message_type = MessageType.COMPLIMENT
    order.address_mode = AddressMode.INFORMAL
    return order


def _invite(order_id: object, *, status: InviteStatus = InviteStatus.PENDING) -> MagicMock:
    invite = MagicMock()
    invite.order_id = order_id
    invite.token = "abc123"
    invite.status = status
    return invite


def test_parse_payload_from_start_and_raw() -> None:
    assert parse_invite_payload("/start inv_abc123") == "abc123"
    assert parse_invite_payload("inv_abc123") == "abc123"
    assert parse_invite_payload("/start") is None
    assert parse_invite_payload("hello") is None


def test_build_invite_link_strips_at() -> None:
    assert (
        build_invite_link("@MyBot", "tok") == f"https://t.me/MyBot?start={INVITE_PAYLOAD_PREFIX}tok"
    )


async def test_resolve_accepts_matching_username() -> None:
    service, _session, invites, orders = _service()
    order = _order()
    invite = _invite(order.id)
    invites.get_by_token.return_value = invite
    orders.get_by_id.return_value = order

    resolved_invite, resolved_order = await service.resolve("inv_abc123", "@Ivan_Petrov")

    assert resolved_invite is invite
    assert resolved_order is order
    assert invite.status is InviteStatus.PENDING


async def test_resolve_rejects_missing_username_without_consuming() -> None:
    service, _session, invites, orders = _service()
    order = _order()
    invite = _invite(order.id)
    invites.get_by_token.return_value = invite
    orders.get_by_id.return_value = order

    with pytest.raises(UsernameMissingError):
        await service.resolve("inv_abc123", None)

    assert invite.status is InviteStatus.PENDING


async def test_resolve_rejects_mismatched_username_without_consuming() -> None:
    service, _session, invites, orders = _service()
    order = _order()
    invite = _invite(order.id)
    invites.get_by_token.return_value = invite
    orders.get_by_id.return_value = order

    with pytest.raises(UsernameMismatchError):
        await service.resolve("inv_abc123", "other_user")

    assert invite.status is InviteStatus.PENDING


async def test_resolve_rejects_unknown_token() -> None:
    service, _session, invites, _orders = _service()
    invites.get_by_token.return_value = None

    with pytest.raises(InviteNotFoundError):
        await service.resolve("inv_missing", "ivan_petrov")


async def test_issue_marks_order_pending_and_keeps_token() -> None:
    service, session, invites, _orders = _service()
    order = _order()
    order.status = OrderStatus.DRAFT
    invite = _invite(order.id)
    invites.get_by_order_id.return_value = invite

    issued = await service.issue(order, "ComplimentBot")

    assert order.status is OrderStatus.PENDING
    assert issued.token == "abc123"
    assert issued.link == "https://t.me/ComplimentBot?start=inv_abc123"
    invites.create.assert_not_awaited()
    session.commit.assert_awaited_once()


async def test_resolve_rejects_used_invite() -> None:
    service, _session, invites, _orders = _service()
    invite = _invite(uuid4(), status=InviteStatus.ACCEPTED)
    invites.get_by_token.return_value = invite

    with pytest.raises(InviteNotPendingError):
        await service.resolve("inv_abc123", "ivan_petrov")
