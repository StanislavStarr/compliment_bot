import uuid

from aiogram import F, Router
from aiogram.filters import StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery
from sqlalchemy.ext.asyncio import AsyncSession

from app.application.orders.service import OpenOrderExistsError
from app.application.recipient_onboarding.service import (
    RecipientOnboardingError,
    RecipientOnboardingService,
)
from app.infrastructure.db.models.orders import Invite, Order
from app.infrastructure.db.models.users import User
from app.infrastructure.telegram.helpers import Event, cb_message, send
from app.infrastructure.telegram.keyboards.recipient import recipient_consent_keyboard
from app.infrastructure.telegram.notices import deliver_counterpart_notice
from app.infrastructure.telegram.routers.recipient.schedule import render_timezone
from app.infrastructure.telegram.states.recipient import RecipientOnboarding

router = Router(name="recipient_consent")


async def render_recipient_consent(event: Event, state: FSMContext, text: str) -> None:
    await state.set_state(RecipientOnboarding.consent)
    await send(event, text, recipient_consent_keyboard())


@router.callback_query(F.data == "invite:accept", StateFilter(RecipientOnboarding.consent))
async def on_invite_accept(
    callback: CallbackQuery, state: FSMContext, session: AsyncSession
) -> None:
    service = RecipientOnboardingService(session)
    user, invite, order = await _load_invite_context(callback, state, service)
    await callback.answer()
    await cb_message(callback).edit_reply_markup(reply_markup=None)
    if user is None or invite is None or order is None:
        return
    await service.confirm_consent(user)
    try:
        await service.accept(invite, order, user)
    except (RecipientOnboardingError, OpenOrderExistsError) as exc:
        await send(callback, str(exc))
        return
    await render_timezone(callback, state)


@router.callback_query(F.data == "invite:decline", StateFilter(RecipientOnboarding.consent))
async def on_invite_decline(
    callback: CallbackQuery, state: FSMContext, session: AsyncSession
) -> None:
    service = RecipientOnboardingService(session)
    _user, _invite, order = await _load_invite_context(callback, state, service)
    await callback.answer()
    await cb_message(callback).edit_reply_markup(reply_markup=None)
    if order is None:
        return
    notice = await service.decline(order)
    await state.clear()
    await send(callback, "Хорошо, заказ остановлен. Сообщения приходить не будут.")
    if notice is not None and callback.bot is not None:
        await deliver_counterpart_notice(callback.bot, notice)


async def _load_invite_context(
    callback: CallbackQuery, state: FSMContext, service: RecipientOnboardingService
) -> tuple[User | None, Invite | None, Order | None]:
    if callback.from_user is None:
        return None, None, None
    user = await service.users.get_by_telegram_id(callback.from_user.id)
    data = await state.get_data()
    order_raw = data.get("order_id")
    if user is None or order_raw is None:
        await send(callback, "Откройте приглашение ещё раз по ссылке.")
        return None, None, None
    invite = await service.invites.get_by_order_id(uuid.UUID(order_raw))
    order = await service.orders.get_by_id(uuid.UUID(order_raw))
    if invite is None or order is None:
        await send(callback, "Приглашение уже недействительно.")
        return user, None, None
    return user, invite, order
