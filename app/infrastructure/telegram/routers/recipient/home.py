from aiogram.fsm.context import FSMContext
from sqlalchemy.ext.asyncio import AsyncSession

from app.application.recipient_onboarding.service import RecipientOnboardingService
from app.infrastructure.db.models.users import User
from app.infrastructure.telegram.helpers import Event, send, telegram_user_id
from app.infrastructure.telegram.keyboards.settings import (
    recipient_home_keyboard,
    stopped_profile_keyboard,
)
from app.infrastructure.telegram.routers.admin import is_admin_telegram_id
from app.infrastructure.telegram.routers.recipient.copy import (
    ORDER_STOPPED,
    RECIPIENT_HOME,
    RECIPIENT_PAUSED,
)


async def render_recipient_home(
    event: Event, state: FSMContext, session: AsyncSession, user: User
) -> None:
    await state.clear()
    service = RecipientOnboardingService(session)
    order = await service.orders.get_open_for_recipient(user.id)
    if order is None:
        await send(event, ORDER_STOPPED, stopped_profile_keyboard())
        return

    schedule = await service.schedules.get_by_user_id(user.id)
    paused = schedule is None or not schedule.is_active
    text = RECIPIENT_PAUSED if paused else RECIPIENT_HOME
    await send(
        event,
        text,
        recipient_home_keyboard(
            paused=paused, is_admin=is_admin_telegram_id(telegram_user_id(event))
        ),
    )
