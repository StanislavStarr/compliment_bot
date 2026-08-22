from aiogram import Router
from aiogram.filters import Command, CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.types import Message
from sqlalchemy.ext.asyncio import AsyncSession

from app.application.onboarding.service import OnboardingService
from app.domain.users.enums import OnboardingStep, UserStatus
from app.infrastructure.telegram.routers.onboarding import render_current_step
from app.infrastructure.telegram.routers.settings import render_settings

router = Router(name="start")


@router.message(CommandStart())
async def on_start(message: Message, state: FSMContext, session: AsyncSession) -> None:
    assert message.from_user is not None
    service = OnboardingService(session)
    user = await service.get_or_create_user(
        telegram_user_id=message.from_user.id, telegram_chat_id=message.chat.id
    )

    if user.onboarding_step == OnboardingStep.DONE and user.status in {
        UserStatus.ACTIVE,
        UserStatus.PAUSED,
    }:
        await render_settings(message, state, session, user)
        return

    await render_current_step(message, state, service, user)


@router.message(Command("help"))
async def on_help(message: Message) -> None:
    await message.answer(
        "Этот бот раз в день присылает короткий персональный комплимент или слова "
        "поддержки.\n\n"
        "/start — начать или открыть настройки\n"
        "/settings — профиль и расписание\n"
        "/pause — приостановить сообщения\n"
        "/resume — возобновить\n"
        "/delete — удалить профиль"
    )
