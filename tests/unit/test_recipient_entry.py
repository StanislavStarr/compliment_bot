from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

from app.application.invites.service import (
    InviteNotFoundError,
    UsernameMismatchError,
    UsernameMissingError,
)
from app.application.orders.notices import CounterpartNotice, NoticeKind
from app.domain.messages.enums import MessageType
from app.domain.users.enums import RecipientOnboardingStep
from app.infrastructure.telegram.notices import format_counterpart_notice
from app.infrastructure.telegram.routers.recipient.entry import (
    consent_prompt,
    handle_invite_start,
    invite_error_message,
    resume_recipient_without_payload,
)
from app.infrastructure.telegram.routers.recipient.schedule import parse_hh_mm


def _message(*, username: str | None = "ivan_petrov") -> MagicMock:
    message = MagicMock()
    message.from_user = MagicMock()
    message.from_user.id = 42
    message.from_user.username = username
    message.chat.id = 100
    message.answer = AsyncMock()
    return message


def _order(*, message_type: MessageType = MessageType.COMPLIMENT) -> MagicMock:
    order = MagicMock()
    order.id = uuid4()
    order.author_id = uuid4()
    order.message_type = message_type
    return order


def test_invite_error_messages() -> None:
    assert "нет username" in invite_error_message(UsernameMissingError("x"))
    assert "другого аккаунта" in invite_error_message(UsernameMismatchError("x"))
    assert "не найдено" in invite_error_message(InviteNotFoundError("x"))


def test_consent_prompt_names_author_and_genre() -> None:
    order = _order()
    text = consent_prompt("alice", order)
    assert "@alice" in text
    assert "комплименты" in text
    assert "совершеннолетних" in text

    support = consent_prompt("alice", _order(message_type=MessageType.SUPPORT))
    assert "поддержки" in support


def test_format_counterpart_notices() -> None:
    declined = CounterpartNotice(
        telegram_chat_id=1,
        kind=NoticeKind.RECIPIENT_DECLINED,
        author_username="alice",
        recipient_username="ivan_petrov",
    )
    assert "@ivan_petrov" in format_counterpart_notice(declined)
    assert "отказался" in format_counterpart_notice(declined)

    stopped = CounterpartNotice(
        telegram_chat_id=1,
        kind=NoticeKind.RECIPIENT_STOPPED,
        author_username="alice",
        recipient_username="ivan_petrov",
    )
    assert "остановил" in format_counterpart_notice(stopped)


async def test_invite_start_mismatch_does_not_create_user() -> None:
    message = _message(username="other")
    resolve = AsyncMock(side_effect=UsernameMismatchError("x"))
    with (
        patch("app.infrastructure.telegram.routers.recipient.entry.InviteService") as invite_cls,
        patch(
            "app.infrastructure.telegram.routers.recipient.entry.RecipientOnboardingService"
        ) as recipient_cls,
    ):
        invite_cls.return_value.resolve = resolve
        await handle_invite_start(message, AsyncMock(), AsyncMock(), "inv_abc")

    recipient_cls.assert_not_called()
    message.answer.assert_awaited_once()
    assert "другого аккаунта" in message.answer.await_args.args[0]


async def test_invite_start_unknown_token_does_not_create_user() -> None:
    message = _message()
    with (
        patch("app.infrastructure.telegram.routers.recipient.entry.InviteService") as invite_cls,
        patch(
            "app.infrastructure.telegram.routers.recipient.entry.RecipientOnboardingService"
        ) as recipient_cls,
    ):
        invite_cls.return_value.resolve = AsyncMock(side_effect=InviteNotFoundError("x"))
        await handle_invite_start(message, AsyncMock(), AsyncMock(), "inv_missing")

    recipient_cls.assert_not_called()
    assert "не найдено" in message.answer.await_args.args[0]


async def test_invite_start_ok_creates_recipient_and_asks_consent() -> None:
    message = _message()
    state = AsyncMock()
    invite = MagicMock()
    invite.id = uuid4()
    order = _order()
    user = MagicMock()
    user.id = uuid4()
    author = MagicMock()
    author.telegram_username = "alice"

    with (
        patch("app.infrastructure.telegram.routers.recipient.entry.InviteService") as invite_cls,
        patch(
            "app.infrastructure.telegram.routers.recipient.entry.RecipientOnboardingService"
        ) as recipient_cls,
        patch(
            "app.infrastructure.telegram.routers.recipient.entry.render_recipient_consent",
            new_callable=AsyncMock,
        ) as render,
    ):
        invite_cls.return_value.resolve = AsyncMock(return_value=(invite, order))
        service: Any = recipient_cls.return_value
        service.get_or_create_user = AsyncMock(return_value=user)
        service.users.get_by_id = AsyncMock(return_value=author)
        await handle_invite_start(message, state, AsyncMock(), "inv_abc")

    service.get_or_create_user.assert_awaited_once()
    state.update_data.assert_awaited_once()
    render.assert_awaited_once()
    assert render.await_args is not None
    assert "@alice" in render.await_args.args[2]
    assert "комплименты" in render.await_args.args[2]


async def test_resume_recipient_after_accept_renders_slot() -> None:
    message = _message()
    user = MagicMock()
    user.recipient_step = RecipientOnboardingStep.TIMEZONE
    with patch(
        "app.infrastructure.telegram.routers.recipient.entry.render_recipient_step",
        new_callable=AsyncMock,
    ) as render:
        await resume_recipient_without_payload(message, AsyncMock(), AsyncMock(), user)
    render.assert_awaited_once()


async def test_resume_recipient_done_shows_home() -> None:
    message = _message()
    user = MagicMock()
    user.recipient_step = RecipientOnboardingStep.DONE
    with patch(
        "app.infrastructure.telegram.routers.recipient.entry.render_recipient_home",
        new_callable=AsyncMock,
    ) as render:
        await resume_recipient_without_payload(message, AsyncMock(), AsyncMock(), user)
    render.assert_awaited_once()


def test_parse_hh_mm() -> None:
    parsed = parse_hh_mm("08:30")
    assert parsed is not None
    assert parsed.hour == 8
    assert parsed.minute == 30
    assert parse_hh_mm("25:00") is None
    assert parse_hh_mm("nope") is None
