from aiogram.fsm.context import FSMContext
from sqlalchemy.ext.asyncio import AsyncSession

from app.application.author_onboarding.service import AuthorOnboardingService
from app.domain.users.enums import AuthorOnboardingStep
from app.infrastructure.db.models.users import User
from app.infrastructure.telegram.helpers import Event, send, telegram_user_id

MAX_STYLE_EXAMPLES = 3


async def get_author(service: AuthorOnboardingService, event: Event) -> User | None:
    user = await service.users.get_by_telegram_id(telegram_user_id(event))
    if user is None:
        await send(event, "Анкета ещё не начата. Отправьте /start.")
    return user


async def finish_section(
    event: Event, state: FSMContext, session: AsyncSession, user: User
) -> None:
    """После сохранения шага: в режиме правки — к резюме, иначе следующий шаг."""
    from app.infrastructure.telegram.routers.author.render import render_author_step
    from app.infrastructure.telegram.routers.author.summary import render_summary

    data = await state.get_data()
    service = AuthorOnboardingService(session)
    order = await service.draft_order(user)
    if data.get("edit_mode"):
        await state.update_data(edit_mode=False)
        await service.set_step(user, AuthorOnboardingStep.SUMMARY)
        await render_summary(event, state, service, user)
        return
    nxt = await service.advance_step(user, order)
    await render_author_step(event, state, service, user, nxt)
