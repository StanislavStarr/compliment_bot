import uuid

from aiogram.fsm.context import FSMContext

from app.application.recipient_onboarding.service import RecipientOnboardingService
from app.domain.orders.enums import OPEN_ORDER_STATUSES
from app.infrastructure.db.models.orders import Order
from app.infrastructure.db.models.users import User
from app.infrastructure.telegram.helpers import Event, send, telegram_user_id


async def get_recipient(service: RecipientOnboardingService, event: Event) -> User | None:
    user = await service.users.get_by_telegram_id(telegram_user_id(event))
    if user is None:
        await send(event, "Откройте приглашение ещё раз по ссылке.")
    return user


async def bound_order(
    service: RecipientOnboardingService, event: Event, state: FSMContext, user: User
) -> Order | None:
    data = await state.get_data()
    order_raw = data.get("order_id")
    order = None
    if order_raw is not None:
        order = await service.orders.get_by_id(uuid.UUID(str(order_raw)))
        if order is not None and order.status not in OPEN_ORDER_STATUSES:
            order = None
    if order is None:
        order = await service.orders.get_open_for_recipient(user.id)
    if order is None or order.recipient_user_id != user.id:
        await send(event, "Откройте приглашение ещё раз по ссылке.")
        return None
    await state.update_data(order_id=str(order.id))
    return order
