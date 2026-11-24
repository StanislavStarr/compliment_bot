from aiogram import F, Router
from aiogram.filters import StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery
from sqlalchemy.ext.asyncio import AsyncSession

from app.application.author_onboarding.service import AuthorOnboardingService
from app.domain.messages.enums import MessageType
from app.infrastructure.telegram.helpers import Event, cb_data, cb_message, send
from app.infrastructure.telegram.keyboards.author import genre_keyboard
from app.infrastructure.telegram.routers.author.common import finish_section, get_author
from app.infrastructure.telegram.states.author import AuthorOnboarding

router = Router(name="author_genre")


async def render_genre(event: Event, state: FSMContext) -> None:
    await state.set_state(AuthorOnboarding.genre)
    await send(
        event,
        "Какие сообщения заказать: короткие комплименты или слова поддержки?\n"
        "Это разные тексты, тип потом нельзя смешать в одном заказе.",
        genre_keyboard(),
    )


@router.callback_query(F.data.startswith("genre:"), StateFilter(AuthorOnboarding.genre))
async def on_genre(callback: CallbackQuery, state: FSMContext, session: AsyncSession) -> None:
    service = AuthorOnboardingService(session)
    user = await get_author(service, callback)
    await callback.answer()
    if user is None:
        return
    message_type = MessageType(cb_data(callback).split(":", 1)[1])
    await service.save_genre(user, message_type)
    await cb_message(callback).edit_reply_markup(reply_markup=None)
    await finish_section(callback, state, session, user)
