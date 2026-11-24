from aiogram import F, Router
from aiogram.filters import StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.types import Message
from sqlalchemy.ext.asyncio import AsyncSession

from app.application.author_onboarding.service import AuthorOnboardingError, AuthorOnboardingService
from app.infrastructure.telegram.helpers import Event, message_text, send
from app.infrastructure.telegram.routers.author.common import finish_section, get_author
from app.infrastructure.telegram.states.author import AuthorOnboarding

router = Router(name="author_recipient")


async def render_recipient_username(event: Event, state: FSMContext) -> None:
    await state.set_state(AuthorOnboarding.recipient_username)
    await send(
        event,
        "Напишите username человека, для которого заказываете сообщения.\n"
        "Например: @ivan_petrov\n\n"
        "Ссылка будет персональной: открыть её сможет только этот аккаунт.",
    )


@router.message(StateFilter(AuthorOnboarding.recipient_username), F.text)
async def on_recipient_username(message: Message, state: FSMContext, session: AsyncSession) -> None:
    service = AuthorOnboardingService(session)
    user = await get_author(service, message)
    if user is None:
        return
    try:
        await service.save_recipient_username(user, message_text(message))
    except AuthorOnboardingError:
        await message.answer("Нужен username вида @name, без пробелов. Попробуйте ещё раз.")
        return
    await finish_section(message, state, session, user)
