from aiogram.fsm.context import FSMContext
from aiogram.types import Message
from sqlalchemy.ext.asyncio import AsyncSession

from app.application.invites.service import (
    InviteError,
    InviteNotFoundError,
    InviteNotPendingError,
    InviteService,
    UsernameMismatchError,
    UsernameMissingError,
    parse_invite_payload,
)
from app.application.recipient_onboarding.service import RecipientOnboardingService
from app.domain.messages.enums import MessageType
from app.domain.orders.enums import InviteStatus
from app.domain.users.enums import RecipientOnboardingStep
from app.infrastructure.db.models.orders import Order
from app.infrastructure.db.models.users import User
from app.infrastructure.db.repositories.users import UserRepository
from app.infrastructure.telegram.routers.recipient.consent import render_recipient_consent
from app.infrastructure.telegram.routers.recipient.copy import (
    RECIPIENT_ONLY_BY_LINK,
)
from app.infrastructure.telegram.routers.recipient.home import render_recipient_home
from app.infrastructure.telegram.routers.recipient.render import render_recipient_step


def invite_error_message(error: InviteError) -> str:
    if isinstance(error, UsernameMissingError):
        return (
            "У этого аккаунта нет username (@ник). Укажите его в настройках Telegram "
            "и откройте ссылку ещё раз. Приглашение осталось действительным."
        )
    if isinstance(error, UsernameMismatchError):
        return "Эта ссылка предназначена для другого аккаунта. Приглашение не использовано."
    if isinstance(error, InviteNotPendingError):
        return "Это приглашение уже использовано или отозвано."
    if isinstance(error, InviteNotFoundError):
        return "Приглашение не найдено или уже не действует."
    return "Не удалось открыть приглашение."


def consent_prompt(author_username: str | None, order: Order) -> str:
    author = f"@{author_username}" if author_username else "человек"
    if order.message_type is MessageType.SUPPORT:
        genre = "слова поддержки"
    else:
        genre = "короткие комплименты"
    return (
        f"{author} пригласил вас сюда и заказал для вас {genre}.\n\n"
        "Готовы получать эти сообщения? Отправитель указан явно — это не анонимный заказ.\n"
        "Сервис для совершеннолетних."
    )


async def resume_recipient_without_payload(
    message: Message, state: FSMContext, session: AsyncSession, user: User
) -> None:
    if user.recipient_step is RecipientOnboardingStep.DONE:
        await render_recipient_home(message, state, session, user)
        return
    if user.recipient_step in {
        RecipientOnboardingStep.TIMEZONE,
        RecipientOnboardingStep.SCHEDULE_MODE,
        RecipientOnboardingStep.SCHEDULE_TIME,
    }:
        await render_recipient_step(message, state, session, user)
        return
    await message.answer(RECIPIENT_ONLY_BY_LINK)


async def handle_invite_start(
    message: Message, state: FSMContext, session: AsyncSession, payload: str
) -> None:
    assert message.from_user is not None
    invites = InviteService(session)
    try:
        invite, order = await invites.resolve(payload, message.from_user.username)
    except InviteNotPendingError as exc:
        if await _resume_accepted_invite(message, state, session, payload):
            return
        await message.answer(invite_error_message(exc))
        return
    except InviteError as exc:
        await message.answer(invite_error_message(exc))
        return

    service = RecipientOnboardingService(session)
    user = await service.get_or_create_user(
        telegram_user_id=message.from_user.id,
        telegram_chat_id=message.chat.id,
        telegram_username=message.from_user.username,
    )
    if user.id == order.author_id:
        await message.answer("Нельзя принять собственное приглашение.")
        return

    author = await service.users.get_by_id(order.author_id)
    await state.update_data(invite_id=str(invite.id), order_id=str(order.id))
    await render_recipient_consent(
        message, state, consent_prompt(author.telegram_username if author else None, order)
    )


async def _resume_accepted_invite(
    message: Message, state: FSMContext, session: AsyncSession, payload: str
) -> bool:
    if message.from_user is None:
        return False
    token = parse_invite_payload(payload)
    if token is None:
        return False
    invites = InviteService(session)
    invite = await invites.invites.get_by_token(token)
    if invite is None or invite.status is not InviteStatus.ACCEPTED:
        return False
    order = await invites.orders.get_by_id(invite.order_id)
    user = await UserRepository(session).get_by_telegram_id(message.from_user.id)
    if order is None or user is None or order.recipient_user_id != user.id:
        return False
    if user.recipient_step is RecipientOnboardingStep.DONE:
        await render_recipient_home(message, state, session, user)
        return True
    await render_recipient_step(message, state, session, user)
    return True
