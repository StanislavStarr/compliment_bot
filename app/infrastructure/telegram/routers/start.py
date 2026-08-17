from aiogram import Router
from aiogram.filters import Command, CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.types import Message
from sqlalchemy.ext.asyncio import AsyncSession

from app.application.onboarding.service import OnboardingService
from app.domain.users.enums import OnboardingStep, UserStatus
from app.infrastructure.telegram.routers.onboarding import render_current_step

router = Router(name="start")


@router.message(CommandStart())
async def on_start(message: Message, state: FSMContext, session: AsyncSession) -> None:
    assert message.from_user is not None
    service = OnboardingService(session)
    user = await service.get_or_create_user(
        telegram_user_id=message.from_user.id, telegram_chat_id=message.chat.id
    )

    if user.status == UserStatus.ACTIVE and user.onboarding_step == OnboardingStep.DONE:
        await state.clear()
        await message.answer(
            "Вы уже зарегистрированы, профиль настроен. Управление настройками "
            "будет добавлено на следующем этапе разработки."
        )
        return

    await render_current_step(message, state, service, user)


@router.message(Command("help"))
async def on_help(message: Message) -> None:
    await message.answer(
        "Этот бот раз в день присылает короткий персональный комплимент или слова "
        "поддержки. Отправьте /start, чтобы начать или продолжить настройку профиля."
    )
