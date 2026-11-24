from aiogram.fsm.context import FSMContext
from sqlalchemy.ext.asyncio import AsyncSession

from app.application.recipient_onboarding.service import RecipientOnboardingService
from app.domain.users.enums import RecipientOnboardingStep
from app.infrastructure.db.models.users import User
from app.infrastructure.telegram.helpers import Event, send
from app.infrastructure.telegram.routers.recipient.copy import ORDER_STOPPED
from app.infrastructure.telegram.routers.recipient.home import render_recipient_home
from app.infrastructure.telegram.routers.recipient.schedule import (
    finish_recipient_onboarding,
    render_schedule_mode,
    render_timezone,
)


async def render_recipient_step(
    event: Event, state: FSMContext, session: AsyncSession, user: User
) -> None:
    service = RecipientOnboardingService(session)
    step = user.recipient_step
    if step is RecipientOnboardingStep.DONE:
        await render_recipient_home(event, state, session, user)
        return

    order = await service.orders.get_open_for_recipient(user.id)
    if order is None:
        await send(event, ORDER_STOPPED)
        return
    await state.update_data(order_id=str(order.id))

    schedule = await service.schedules.get_by_user_id(user.id)
    if schedule is not None and step in {
        RecipientOnboardingStep.TIMEZONE,
        RecipientOnboardingStep.SCHEDULE_MODE,
        RecipientOnboardingStep.SCHEDULE_TIME,
    }:
        await service.complete(user, order)
        await finish_recipient_onboarding(event, state, session, user)
        return

    data = await state.get_data()
    if step in {
        RecipientOnboardingStep.SCHEDULE_MODE,
        RecipientOnboardingStep.SCHEDULE_TIME,
    } and isinstance(data.get("timezone_name"), str):
        await render_schedule_mode(event, state)
        return
    await render_timezone(event, state)
