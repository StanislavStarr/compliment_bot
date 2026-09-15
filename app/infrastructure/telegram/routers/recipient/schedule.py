from datetime import time
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from aiogram import F, Router
from aiogram.filters import StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message
from sqlalchemy.ext.asyncio import AsyncSession

from app.application.recipient_onboarding.service import (
    RecipientOnboardingError,
    RecipientOnboardingService,
)
from app.domain.schedules.enums import Period, ScheduleMode
from app.domain.users.constants import TIMEZONE_MANUAL_OPTION_CODE
from app.domain.users.enums import RecipientOnboardingStep
from app.infrastructure.db.models.users import User
from app.infrastructure.telegram.helpers import Event, cb_data, cb_message, clear_markup, send
from app.infrastructure.telegram.keyboards.recipient import (
    exact_time_keyboard,
    period_keyboard,
    schedule_mode_keyboard,
    timezone_keyboard,
)
from app.infrastructure.telegram.routers.recipient.common import bound_order, get_recipient
from app.infrastructure.telegram.routers.recipient.copy import SLOT_COMPLETE, SLOT_UPDATED
from app.infrastructure.telegram.states.recipient import RecipientOnboarding
from app.infrastructure.telegram.unscheduled import send_unscheduled_message

router = Router(name="recipient_schedule")


def parse_hh_mm(value: str) -> time | None:
    try:
        hour_str, minute_str = value.strip().split(":")
        return time(hour=int(hour_str), minute=int(minute_str))
    except (ValueError, IndexError):
        return None


async def render_timezone(event: Event, state: FSMContext) -> None:
    await state.set_state(RecipientOnboarding.timezone_select)
    await send(event, "В каком часовом поясе вы находитесь?", timezone_keyboard())


async def render_schedule_mode(event: Event, state: FSMContext) -> None:
    await state.set_state(RecipientOnboarding.schedule_mode)
    await send(
        event,
        "Как присылать сообщение — в точное время или в течение периода дня?",
        schedule_mode_keyboard(),
    )


@router.callback_query(
    F.data.startswith("tz:set:"), StateFilter(RecipientOnboarding.timezone_select)
)
async def on_timezone_set(
    callback: CallbackQuery, state: FSMContext, session: AsyncSession
) -> None:
    service = RecipientOnboardingService(session)
    user = await get_recipient(service, callback)
    await callback.answer()
    await clear_markup(callback)
    if user is None:
        return
    await state.update_data(timezone_name=cb_data(callback).split(":", 2)[2])
    await _to_schedule_mode(callback, state, service, user)


@router.callback_query(
    F.data == f"tz:{TIMEZONE_MANUAL_OPTION_CODE}",
    StateFilter(RecipientOnboarding.timezone_select),
)
async def on_timezone_manual_prompt(callback: CallbackQuery, state: FSMContext) -> None:
    await callback.answer()
    await clear_markup(callback)
    await state.set_state(RecipientOnboarding.timezone_manual)
    await send(
        callback, "Введите часовой пояс в формате IANA, например Europe/Moscow или Asia/Almaty."
    )


@router.message(StateFilter(RecipientOnboarding.timezone_manual), F.text)
async def on_timezone_manual_text(
    message: Message, state: FSMContext, session: AsyncSession
) -> None:
    assert message.text is not None
    candidate = message.text.strip()
    try:
        ZoneInfo(candidate)
    except (ZoneInfoNotFoundError, ValueError):
        await message.answer(
            "Не удалось распознать часовой пояс. Попробуйте формат Europe/Moscow или Asia/Almaty."
        )
        return
    service = RecipientOnboardingService(session)
    user = await get_recipient(service, message)
    if user is None:
        return
    await state.update_data(timezone_name=candidate)
    await _to_schedule_mode(message, state, service, user)


async def _to_schedule_mode(
    event: Event, state: FSMContext, service: RecipientOnboardingService, user: User
) -> None:
    data = await state.get_data()
    if not data.get("settings_edit"):
        await service.set_step(user, RecipientOnboardingStep.SCHEDULE_MODE)
    await render_schedule_mode(event, state)


@router.callback_query(
    F.data.startswith("sched_mode:"), StateFilter(RecipientOnboarding.schedule_mode)
)
async def on_schedule_mode(
    callback: CallbackQuery, state: FSMContext, session: AsyncSession
) -> None:
    service = RecipientOnboardingService(session)
    user = await get_recipient(service, callback)
    await callback.answer()
    await clear_markup(callback)
    if user is None:
        return
    mode = ScheduleMode(cb_data(callback).split(":", 1)[1])
    data = await state.get_data()
    if not data.get("settings_edit"):
        await service.set_step(user, RecipientOnboardingStep.SCHEDULE_TIME)
    if mode is ScheduleMode.EXACT:
        await state.set_state(RecipientOnboarding.schedule_time_select)
        await send(callback, "Выберите удобное время.", exact_time_keyboard())
        return
    await state.set_state(RecipientOnboarding.schedule_period_select)
    await send(callback, "Выберите период дня.", period_keyboard())


@router.callback_query(
    F.data.startswith("sched_time:pick:"),
    StateFilter(RecipientOnboarding.schedule_time_select),
)
async def on_schedule_time_pick(
    callback: CallbackQuery, state: FSMContext, session: AsyncSession
) -> None:
    time_str = cb_data(callback).split(":", 2)[2]
    await callback.answer()
    await clear_markup(callback)
    await _finalize_exact_schedule(callback, state, session, time_str)


@router.callback_query(
    F.data == "sched_time:manual", StateFilter(RecipientOnboarding.schedule_time_select)
)
async def on_schedule_time_manual_prompt(callback: CallbackQuery, state: FSMContext) -> None:
    await callback.answer()
    await clear_markup(callback)
    await state.set_state(RecipientOnboarding.schedule_time_manual)
    await send(callback, "Введите время в формате ЧЧ:ММ, например 08:30.")


@router.message(StateFilter(RecipientOnboarding.schedule_time_manual), F.text)
async def on_schedule_time_manual_text(
    message: Message, state: FSMContext, session: AsyncSession
) -> None:
    assert message.text is not None
    await _finalize_exact_schedule(message, state, session, message.text.strip())


async def _finalize_exact_schedule(
    event: Event, state: FSMContext, session: AsyncSession, time_str: str
) -> None:
    exact_time = parse_hh_mm(time_str)
    if exact_time is None:
        await send(
            event, "Не удалось распознать время. Введите его в формате ЧЧ:ММ, например 08:30."
        )
        return
    data = await state.get_data()
    timezone_name = data.get("timezone_name")
    if not isinstance(timezone_name, str):
        await render_timezone(event, state)
        return
    await _save_slot_and_activate(
        event, state, session, timezone_name, ScheduleMode.EXACT, exact_local_time=exact_time
    )


@router.callback_query(
    F.data.startswith("sched_period:"),
    StateFilter(RecipientOnboarding.schedule_period_select),
)
async def on_schedule_period(
    callback: CallbackQuery, state: FSMContext, session: AsyncSession
) -> None:
    period = Period(cb_data(callback).split(":", 1)[1])
    await callback.answer()
    await clear_markup(callback)
    data = await state.get_data()
    timezone_name = data.get("timezone_name")
    if not isinstance(timezone_name, str):
        await render_timezone(callback, state)
        return
    await _save_slot_and_activate(
        callback, state, session, timezone_name, ScheduleMode.PERIOD, period=period
    )


async def _save_slot_and_activate(
    event: Event,
    state: FSMContext,
    session: AsyncSession,
    timezone_name: str,
    mode: ScheduleMode,
    *,
    exact_local_time: time | None = None,
    period: Period | None = None,
) -> None:
    service = RecipientOnboardingService(session)
    user = await get_recipient(service, event)
    if user is None:
        return
    order = await bound_order(service, event, state, user)
    if order is None:
        return
    try:
        await service.finalize_schedule(
            user, order, timezone_name, mode, exact_local_time=exact_local_time, period=period
        )
        data = await state.get_data()
        if data.get("settings_edit"):
            await state.clear()
            await send(event, SLOT_UPDATED)
            from app.infrastructure.telegram.routers.recipient.home import render_recipient_home

            await render_recipient_home(event, state, session, user)
            return
        await service.complete(user, order)
    except RecipientOnboardingError as exc:
        await send(event, str(exc))
        return
    await finish_recipient_onboarding(event, state, session, user)


async def finish_recipient_onboarding(
    event: Event, state: FSMContext, session: AsyncSession, user: User
) -> None:
    await state.clear()
    await send(event, SLOT_COMPLETE)
    target = cb_message(event) if isinstance(event, CallbackQuery) else event
    await send_unscheduled_message(target, session, user)
