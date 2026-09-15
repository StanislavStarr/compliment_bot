from aiogram import Router
from aiogram.filters import Command, CommandObject, CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.types import Message
from sqlalchemy.ext.asyncio import AsyncSession

from app.application.author_onboarding.service import AuthorOnboardingService
from app.application.invites.service import parse_invite_payload
from app.domain.users.enums import AuthorOnboardingStep, UserRole
from app.infrastructure.telegram.routers.author import render_author_home, render_author_step
from app.infrastructure.telegram.routers.recipient.entry import (
    handle_invite_start,
    resume_recipient_without_payload,
)

router = Router(name="start")

_NO_USERNAME = (
    "Чтобы заказать сообщения, в Telegram должен быть username (@ник). "
    "Укажите его в настройках и снова нажмите /start — адресат увидит, кто пригласил."
)


@router.message(CommandStart())
async def on_start(
    message: Message, command: CommandObject, state: FSMContext, session: AsyncSession
) -> None:
    assert message.from_user is not None
    args = command.args

    if args:
        if parse_invite_payload(args) is not None:
            await handle_invite_start(message, state, session, args)
            return
        await message.answer("Бот доступен только по персональной ссылке-приглашению.")
        return

    if message.from_user.username is None:
        await message.answer(_NO_USERNAME)
        return

    service = AuthorOnboardingService(session)
    user = await service.get_or_create_user(
        telegram_user_id=message.from_user.id,
        telegram_chat_id=message.chat.id,
        telegram_username=message.from_user.username,
    )
    if user.role is UserRole.RECIPIENT:
        await resume_recipient_without_payload(message, state, session, user)
        return

    if user.author_step is AuthorOnboardingStep.DONE:
        order = await service.orders.get_open_for_author(user)
        if order is None:
            user.author_step = AuthorOnboardingStep.CONSENT
            await session.commit()
            await render_author_step(message, state, service, user)
            return
        await render_author_home(message, state, session, user)
        return

    await render_author_step(message, state, service, user)


@router.message(Command("help"))
async def on_help(message: Message) -> None:
    await message.answer(
        "Этот бот помогает заказать ежедневные комплименты или слова поддержки "
        "для другого человека.\n\n"
        "/start — начать заказ или показать ссылку\n"
        "/settings — заказ, пауза или отмена\n"
        "/pause /resume — пауза доставки (адресат)\n"
        "/delete — удалить профиль\n\n"
        "Адресат заходит только по персональной ссылке от заказчика."
    )
