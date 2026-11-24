from aiogram import F, Router
from aiogram.filters import StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery
from sqlalchemy.ext.asyncio import AsyncSession

from app.application.author_onboarding.service import AuthorOnboardingService
from app.infrastructure.telegram.helpers import Event, send
from app.infrastructure.telegram.keyboards.common import consent_keyboard
from app.infrastructure.telegram.routers.author.common import finish_section, get_author
from app.infrastructure.telegram.states.author import AuthorOnboarding

router = Router(name="author_consent")


async def render_consent(event: Event, state: FSMContext) -> None:
    await state.set_state(AuthorOnboarding.consent)
    await send(
        event,
        "Привет! Здесь можно заказать ежедневные короткие комплименты или слова "
        "поддержки для другого человека.\n\n"
        "Вы опишете его характер и выберете тип сообщений. Затем получите ссылку — "
        "адресат сам решит, готов ли их получать, и укажет удобное время.\n\n"
        "Сервис для совершеннолетних. Данные из анкеты нужны только для персонализации "
        "и не передаются третьим лицам.\n\n"
        "Чтобы адресат видел, кто заказал сообщения, у вас должен быть username в Telegram.",
        consent_keyboard(),
    )


@router.callback_query(F.data == "consent:accept", StateFilter(AuthorOnboarding.consent))
async def on_consent_accept(
    callback: CallbackQuery, state: FSMContext, session: AsyncSession
) -> None:
    service = AuthorOnboardingService(session)
    user = await get_author(service, callback)
    await callback.answer()
    if user is None:
        return
    if callback.from_user is None or callback.from_user.username is None:
        await send(
            callback,
            "Сначала укажите username в настройках Telegram (@ник) и снова нажмите /start. "
            "Без него адресат не увидит, кто его пригласил.",
        )
        return
    await service.confirm_consent(user)
    await finish_section(callback, state, session, user)
