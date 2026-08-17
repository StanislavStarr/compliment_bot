import uuid
from collections.abc import Awaitable, Callable
from datetime import time as time_cls
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from aiogram import F, Router
from aiogram.filters import StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, InlineKeyboardMarkup, Message
from sqlalchemy.ext.asyncio import AsyncSession

from app.application.onboarding.service import OnboardingService, OnboardingSummary
from app.domain.profiles.constants import SUPPORT_PREFERENCE_OPTIONS
from app.domain.schedules.enums import PERIOD_LABELS, Period, ScheduleMode
from app.domain.topics.enums import MAX_ACTIVE_TOPICS_PER_USER
from app.domain.users.constants import TIMEZONE_MANUAL_OPTION_CODE
from app.domain.users.enums import AddressMode, OnboardingStep
from app.infrastructure.db.models.users import User
from app.infrastructure.telegram.keyboards.onboarding import (
    address_mode_keyboard,
    consent_keyboard,
    edit_menu_keyboard,
    exact_time_keyboard,
    multi_select_keyboard,
    period_keyboard,
    schedule_mode_keyboard,
    skip_keyboard,
    summary_keyboard,
    timezone_keyboard,
)
from app.infrastructure.telegram.states.onboarding import Onboarding

router = Router(name="onboarding")

MAX_STYLE_EXAMPLES = 3

Event = Message | CallbackQuery


def _cb_data(callback: CallbackQuery) -> str:
    """`callback.data` типизирован как `str | None`, но у наших хендлеров он
    всегда задан — иначе не сработал бы фильтр `F.data...` при регистрации."""
    assert callback.data is not None
    return callback.data


def _cb_message(callback: CallbackQuery) -> Message:
    """Аналогично `callback.data` — сообщение недоступно, только если оно
    старше 48 часов или удалено; для нашего короткого онбординга это не
    ожидается, но mypy требует явного сужения типа."""
    assert isinstance(callback.message, Message)
    return callback.message


def _text(message: Message) -> str:
    assert message.text is not None
    return message.text


def _user_id(event: Event) -> int:
    assert event.from_user is not None
    return event.from_user.id


async def _send(event: Event, text: str, keyboard: InlineKeyboardMarkup | None = None) -> None:
    target = _cb_message(event) if isinstance(event, CallbackQuery) else event
    await target.answer(text, reply_markup=keyboard)


async def _get_user(service: OnboardingService, event: Event) -> User | None:
    user = await service.users.get_by_telegram_id(_user_id(event))
    if user is None:
        await _send(event, "Похоже, анкета ещё не начата. Отправьте /start, чтобы начать заново.")
    return user


async def _finish_section(
    event: Event,
    state: FSMContext,
    service: OnboardingService,
    user: User,
    step_after: OnboardingStep,
    render_next: Callable[[], Awaitable[None]],
) -> None:
    """Общий переход между шагами: если раздел открыт из меню редактирования
    резюме — возвращаемся к резюме, иначе двигаемся дальше по порядку шагов."""
    data = await state.get_data()
    if data.get("edit_mode"):
        await state.update_data(edit_mode=False)
        await service.set_step(user, OnboardingStep.SUMMARY)
        await render_summary(event, state, service, user)
        return
    await service.set_step(user, step_after)
    await render_next()


# --- Согласие и 18+ ---


async def render_consent(event: Event, state: FSMContext) -> None:
    await state.set_state(Onboarding.consent)
    await _send(
        event,
        "Привет! Это бот с ежедневными персональными комплиментами и словами поддержки.\n\n"
        "Сервис предназначен для совершеннолетних пользователей. Отвечая на анкету, "
        "вы соглашаетесь на обработку введённых данных для персонализации сообщений — "
        "они не передаются третьим лицам и не используются для рекламы.\n\n"
        "Анкета займёт 2–3 минуты, каждый ответ сохраняется сразу — если прерветесь, "
        "бот продолжит с того же места.",
        consent_keyboard(),
    )


@router.callback_query(F.data == "consent:accept", StateFilter(Onboarding.consent))
async def on_consent_accept(
    callback: CallbackQuery, state: FSMContext, session: AsyncSession
) -> None:
    service = OnboardingService(session)
    user = await _get_user(service, callback)
    await callback.answer()
    if user is None:
        return
    await service.confirm_consent(user)
    await service.set_step(user, OnboardingStep.ADDRESS_MODE)
    await render_address_mode(callback, state)


# --- Обращение ---


async def render_address_mode(event: Event, state: FSMContext) -> None:
    await state.set_state(Onboarding.address_mode)
    await _send(event, "Как удобнее, чтобы бот к вам обращался?", address_mode_keyboard())


@router.callback_query(F.data.startswith("addr:"), StateFilter(Onboarding.address_mode))
async def on_address_mode(
    callback: CallbackQuery, state: FSMContext, session: AsyncSession
) -> None:
    service = OnboardingService(session)
    user = await _get_user(service, callback)
    await callback.answer()
    if user is None:
        return
    mode = AddressMode(_cb_data(callback).split(":", 1)[1])
    await service.save_address_mode(user, mode)

    async def go_next() -> None:
        await render_qualities(callback, state, service, user)

    await _finish_section(callback, state, service, user, OnboardingStep.QUALITIES, go_next)


# --- Качества ---


async def render_qualities(
    event: Event, state: FSMContext, service: OnboardingService, user: User
) -> None:
    data = await state.get_data()
    selected = set(data.get("selected_quality_ids", []))
    qualities = await service.list_qualities()
    options = [(str(q.id), q.label) for q in qualities]
    await state.update_data(selected_quality_ids=list(selected))
    await state.set_state(Onboarding.qualities_select)
    await _send(
        event,
        "Какие качества вы цените в себе? Можно выбрать несколько.",
        multi_select_keyboard(options, selected, prefix="qual"),
    )


@router.callback_query(F.data.startswith("qual:toggle:"), StateFilter(Onboarding.qualities_select))
async def on_quality_toggle(
    callback: CallbackQuery, state: FSMContext, session: AsyncSession
) -> None:
    service = OnboardingService(session)
    quality_id = _cb_data(callback).split(":", 2)[2]
    data = await state.get_data()
    selected = set(data.get("selected_quality_ids", []))
    if quality_id in selected:
        selected.discard(quality_id)
    else:
        selected.add(quality_id)
    await state.update_data(selected_quality_ids=list(selected))
    await callback.answer()

    qualities = await service.list_qualities()
    options = [(str(q.id), q.label) for q in qualities]
    await _cb_message(callback).edit_reply_markup(
        reply_markup=multi_select_keyboard(options, selected, prefix="qual")
    )


@router.callback_query(F.data == "qual:done", StateFilter(Onboarding.qualities_select))
async def on_qualities_done(
    callback: CallbackQuery, state: FSMContext, session: AsyncSession
) -> None:
    await callback.answer()
    await _cb_message(callback).edit_reply_markup(reply_markup=None)
    await state.set_state(Onboarding.qualities_custom)
    await _send(
        callback,
        "Хотите добавить своими словами, что ещё цените в себе? "
        "Напишите текстом или нажмите «Пропустить».",
        skip_keyboard("qual:skip"),
    )


async def _save_qualities_and_advance(
    event: Event, state: FSMContext, session: AsyncSession, custom_text: str | None
) -> None:
    service = OnboardingService(session)
    user = await _get_user(service, event)
    if user is None:
        return
    data = await state.get_data()
    quality_ids = [uuid.UUID(x) for x in data.get("selected_quality_ids", [])]
    await service.save_qualities(user, quality_ids, custom_text, is_sensitive=False)
    await state.update_data(selected_quality_ids=[])

    async def go_next() -> None:
        await render_topics(event, state, service, user)

    await _finish_section(event, state, service, user, OnboardingStep.TOPICS, go_next)


@router.message(StateFilter(Onboarding.qualities_custom), F.text)
async def on_qualities_custom_text(
    message: Message, state: FSMContext, session: AsyncSession
) -> None:
    await _save_qualities_and_advance(message, state, session, _text(message).strip())


@router.callback_query(F.data == "qual:skip", StateFilter(Onboarding.qualities_custom))
async def on_qualities_custom_skip(
    callback: CallbackQuery, state: FSMContext, session: AsyncSession
) -> None:
    await callback.answer()
    await _cb_message(callback).edit_reply_markup(reply_markup=None)
    await _save_qualities_and_advance(callback, state, session, None)


# --- Темы ---


async def render_topics(
    event: Event, state: FSMContext, service: OnboardingService, user: User
) -> None:
    data = await state.get_data()
    selected = set(data.get("selected_topic_ids", []))
    topics = await service.list_topics()
    options = [(str(t.id), t.label) for t in topics]
    await state.update_data(selected_topic_ids=list(selected))
    await state.set_state(Onboarding.topics_select)
    await _send(
        event,
        f"Выберите до {MAX_ACTIVE_TOPICS_PER_USER} тем, которые для вас важнее всего.",
        multi_select_keyboard(options, selected, prefix="topic"),
    )


@router.callback_query(F.data.startswith("topic:toggle:"), StateFilter(Onboarding.topics_select))
async def on_topic_toggle(
    callback: CallbackQuery, state: FSMContext, session: AsyncSession
) -> None:
    service = OnboardingService(session)
    topic_id = _cb_data(callback).split(":", 2)[2]
    data = await state.get_data()
    selected = set(data.get("selected_topic_ids", []))
    if topic_id in selected:
        selected.discard(topic_id)
    elif len(selected) >= MAX_ACTIVE_TOPICS_PER_USER:
        await callback.answer(f"Максимум {MAX_ACTIVE_TOPICS_PER_USER} темы", show_alert=True)
        return
    else:
        selected.add(topic_id)
    await state.update_data(selected_topic_ids=list(selected))
    await callback.answer()

    topics = await service.list_topics()
    options = [(str(t.id), t.label) for t in topics]
    await _cb_message(callback).edit_reply_markup(
        reply_markup=multi_select_keyboard(options, selected, prefix="topic")
    )


@router.callback_query(F.data == "topic:done", StateFilter(Onboarding.topics_select))
async def on_topics_done(callback: CallbackQuery, state: FSMContext, session: AsyncSession) -> None:
    service = OnboardingService(session)
    user = await _get_user(service, callback)
    await callback.answer()
    await _cb_message(callback).edit_reply_markup(reply_markup=None)
    if user is None:
        return
    data = await state.get_data()
    topic_ids = [uuid.UUID(x) for x in data.get("selected_topic_ids", [])]
    await service.save_topics(user, topic_ids)
    await state.update_data(selected_topic_ids=[])

    async def go_next() -> None:
        await render_support(callback, state, service, user)

    await _finish_section(
        callback, state, service, user, OnboardingStep.SUPPORT_PREFERENCES, go_next
    )


# --- Способ поддержки ---


async def render_support(
    event: Event, state: FSMContext, service: OnboardingService, user: User
) -> None:
    data = await state.get_data()
    selected = set(data.get("selected_support_codes", []))
    await state.update_data(selected_support_codes=list(selected))
    await state.set_state(Onboarding.support_select)
    await _send(
        event,
        "Что обычно помогает почувствовать поддержку? Можно выбрать несколько.",
        multi_select_keyboard(SUPPORT_PREFERENCE_OPTIONS, selected, prefix="supp"),
    )


@router.callback_query(F.data.startswith("supp:toggle:"), StateFilter(Onboarding.support_select))
async def on_support_toggle(callback: CallbackQuery, state: FSMContext) -> None:
    code = _cb_data(callback).split(":", 2)[2]
    data = await state.get_data()
    selected = set(data.get("selected_support_codes", []))
    if code in selected:
        selected.discard(code)
    else:
        selected.add(code)
    await state.update_data(selected_support_codes=list(selected))
    await callback.answer()
    await _cb_message(callback).edit_reply_markup(
        reply_markup=multi_select_keyboard(SUPPORT_PREFERENCE_OPTIONS, selected, prefix="supp")
    )


@router.callback_query(F.data == "supp:done", StateFilter(Onboarding.support_select))
async def on_support_done(callback: CallbackQuery, state: FSMContext) -> None:
    await callback.answer()
    await _cb_message(callback).edit_reply_markup(reply_markup=None)
    await state.set_state(Onboarding.support_custom)
    await _send(
        callback,
        "Хотите уточнить своими словами, что помогает вам почувствовать поддержку? "
        "Напишите текстом или нажмите «Пропустить».",
        skip_keyboard("supp:skip"),
    )


async def _save_support_and_advance(
    event: Event, state: FSMContext, session: AsyncSession, custom_text: str | None
) -> None:
    service = OnboardingService(session)
    user = await _get_user(service, event)
    if user is None:
        return
    data = await state.get_data()
    codes = list(data.get("selected_support_codes", []))
    await service.save_support_preferences(user, codes, custom_text, is_sensitive=False)
    await state.update_data(selected_support_codes=[])

    async def go_next() -> None:
        await render_blocked_topics(event, state, service, user)

    await _finish_section(event, state, service, user, OnboardingStep.BLOCKED_TOPICS, go_next)


@router.message(StateFilter(Onboarding.support_custom), F.text)
async def on_support_custom_text(
    message: Message, state: FSMContext, session: AsyncSession
) -> None:
    await _save_support_and_advance(message, state, session, _text(message).strip())


@router.callback_query(F.data == "supp:skip", StateFilter(Onboarding.support_custom))
async def on_support_custom_skip(
    callback: CallbackQuery, state: FSMContext, session: AsyncSession
) -> None:
    await callback.answer()
    await _cb_message(callback).edit_reply_markup(reply_markup=None)
    await _save_support_and_advance(callback, state, session, None)


# --- Нежелательные темы ---


async def render_blocked_topics(
    event: Event, state: FSMContext, service: OnboardingService, user: User
) -> None:
    data = await state.get_data()
    selected = set(data.get("selected_blocked_codes", []))
    topics = await service.list_topics()
    options = [(t.code, t.label) for t in topics]
    await state.update_data(selected_blocked_codes=list(selected))
    await state.set_state(Onboarding.blocked_select)
    await _send(
        event,
        "Есть темы, которые лучше не затрагивать? Можно выбрать несколько или пропустить этот шаг.",
        multi_select_keyboard(options, selected, prefix="block"),
    )


@router.callback_query(F.data.startswith("block:toggle:"), StateFilter(Onboarding.blocked_select))
async def on_blocked_toggle(
    callback: CallbackQuery, state: FSMContext, session: AsyncSession
) -> None:
    service = OnboardingService(session)
    code = _cb_data(callback).split(":", 2)[2]
    data = await state.get_data()
    selected = set(data.get("selected_blocked_codes", []))
    if code in selected:
        selected.discard(code)
    else:
        selected.add(code)
    await state.update_data(selected_blocked_codes=list(selected))
    await callback.answer()

    topics = await service.list_topics()
    options = [(t.code, t.label) for t in topics]
    await _cb_message(callback).edit_reply_markup(
        reply_markup=multi_select_keyboard(options, selected, prefix="block")
    )


@router.callback_query(F.data == "block:done", StateFilter(Onboarding.blocked_select))
async def on_blocked_done(callback: CallbackQuery, state: FSMContext) -> None:
    await callback.answer()
    await _cb_message(callback).edit_reply_markup(reply_markup=None)
    await state.set_state(Onboarding.blocked_custom)
    await _send(
        callback,
        "Хотите уточнить своими словами что-то ещё, чего лучше избегать? "
        "Напишите текстом или нажмите «Пропустить».",
        skip_keyboard("block:skip"),
    )


async def _save_blocked_and_advance(
    event: Event, state: FSMContext, session: AsyncSession, custom_text: str | None
) -> None:
    service = OnboardingService(session)
    user = await _get_user(service, event)
    if user is None:
        return
    data = await state.get_data()
    codes = list(data.get("selected_blocked_codes", []))
    await service.save_blocked_topics(user, codes, custom_text, is_sensitive=False)
    await state.update_data(selected_blocked_codes=[])

    async def go_next() -> None:
        await render_style_examples(event, state)

    await _finish_section(event, state, service, user, OnboardingStep.STYLE_EXAMPLES, go_next)


@router.message(StateFilter(Onboarding.blocked_custom), F.text)
async def on_blocked_custom_text(
    message: Message, state: FSMContext, session: AsyncSession
) -> None:
    await _save_blocked_and_advance(message, state, session, _text(message).strip())


@router.callback_query(F.data == "block:skip", StateFilter(Onboarding.blocked_custom))
async def on_blocked_custom_skip(
    callback: CallbackQuery, state: FSMContext, session: AsyncSession
) -> None:
    await callback.answer()
    await _cb_message(callback).edit_reply_markup(reply_markup=None)
    await _save_blocked_and_advance(callback, state, session, None)


# --- Примеры понравившихся фраз (необязательно) ---


async def render_style_examples(event: Event, state: FSMContext) -> None:
    await state.update_data(style_examples_count=0)
    await state.set_state(Onboarding.style_examples)
    await _send(
        event,
        f"Необязательный шаг: пришлите 1–{MAX_STYLE_EXAMPLES} примера фраз, которые вам "
        "нравятся (по одной сообщением). Когда закончите — нажмите «Готово».",
        skip_keyboard("style:done", text="Готово / Пропустить"),
    )


@router.message(StateFilter(Onboarding.style_examples), F.text)
async def on_style_example_text(message: Message, state: FSMContext, session: AsyncSession) -> None:
    service = OnboardingService(session)
    user = await _get_user(service, message)
    if user is None:
        return
    await service.add_style_example(user, _text(message).strip())
    data = await state.get_data()
    count = int(data.get("style_examples_count", 0)) + 1
    await state.update_data(style_examples_count=count)

    if count >= MAX_STYLE_EXAMPLES:
        await _finish_style_examples(message, state, service, user)
        return

    await message.answer(
        f"Записал! Можно добавить ещё ({MAX_STYLE_EXAMPLES - count}) или нажать «Готово».",
        reply_markup=skip_keyboard("style:done", text="Готово / Пропустить"),
    )


@router.callback_query(F.data == "style:done", StateFilter(Onboarding.style_examples))
async def on_style_examples_done(
    callback: CallbackQuery, state: FSMContext, session: AsyncSession
) -> None:
    service = OnboardingService(session)
    user = await _get_user(service, callback)
    await callback.answer()
    await _cb_message(callback).edit_reply_markup(reply_markup=None)
    if user is None:
        return
    await _finish_style_examples(callback, state, service, user)


async def _finish_style_examples(
    event: Event, state: FSMContext, service: OnboardingService, user: User
) -> None:
    async def go_next() -> None:
        await render_timezone(event, state)

    await _finish_section(event, state, service, user, OnboardingStep.TIMEZONE, go_next)


# --- Часовой пояс ---


async def render_timezone(event: Event, state: FSMContext) -> None:
    await state.set_state(Onboarding.timezone_select)
    await _send(event, "В каком часовом поясе вы находитесь?", timezone_keyboard())


@router.callback_query(F.data.startswith("tz:set:"), StateFilter(Onboarding.timezone_select))
async def on_timezone_set(
    callback: CallbackQuery, state: FSMContext, session: AsyncSession
) -> None:
    service = OnboardingService(session)
    user = await _get_user(service, callback)
    await callback.answer()
    await _cb_message(callback).edit_reply_markup(reply_markup=None)
    if user is None:
        return
    timezone_name = _cb_data(callback).split(":", 2)[2]
    await state.update_data(timezone_name=timezone_name)
    await _to_schedule_mode(callback, state, service, user)


@router.callback_query(
    F.data == f"tz:{TIMEZONE_MANUAL_OPTION_CODE}", StateFilter(Onboarding.timezone_select)
)
async def on_timezone_manual_prompt(callback: CallbackQuery, state: FSMContext) -> None:
    await callback.answer()
    await _cb_message(callback).edit_reply_markup(reply_markup=None)
    await state.set_state(Onboarding.timezone_manual)
    await _send(
        callback, "Введите часовой пояс в формате IANA, например Europe/Moscow или Asia/Almaty."
    )


@router.message(StateFilter(Onboarding.timezone_manual), F.text)
async def on_timezone_manual_text(
    message: Message, state: FSMContext, session: AsyncSession
) -> None:
    candidate = _text(message).strip()
    try:
        ZoneInfo(candidate)
    except (ZoneInfoNotFoundError, ValueError):
        await message.answer(
            "Не удалось распознать часовой пояс. Попробуйте формат Europe/Moscow или Asia/Almaty."
        )
        return
    service = OnboardingService(session)
    user = await _get_user(service, message)
    if user is None:
        return
    await state.update_data(timezone_name=candidate)
    await _to_schedule_mode(message, state, service, user)


async def _to_schedule_mode(
    event: Event, state: FSMContext, service: OnboardingService, user: User
) -> None:
    """В отличие от других шагов, здесь нельзя использовать `_finish_section`:
    при редактировании раздела "часовой пояс и время" нужно всё равно пройти
    режим/время — иначе расписание не сохранится с новым часовым поясом.
    К резюме возвращаемся только после `finalize_schedule`."""
    await service.set_step(user, OnboardingStep.SCHEDULE_MODE)
    await render_schedule_mode(event, state)


# --- Режим расписания: точное время или период ---


async def render_schedule_mode(event: Event, state: FSMContext) -> None:
    await state.set_state(Onboarding.schedule_mode)
    await _send(
        event,
        "Как присылать сообщение — в точное время или в течение периода дня?",
        schedule_mode_keyboard(),
    )


@router.callback_query(F.data.startswith("sched_mode:"), StateFilter(Onboarding.schedule_mode))
async def on_schedule_mode(
    callback: CallbackQuery, state: FSMContext, session: AsyncSession
) -> None:
    service = OnboardingService(session)
    user = await _get_user(service, callback)
    await callback.answer()
    await _cb_message(callback).edit_reply_markup(reply_markup=None)
    if user is None:
        return
    mode = ScheduleMode(_cb_data(callback).split(":", 1)[1])
    await service.set_step(user, OnboardingStep.SCHEDULE_TIME)
    if mode is ScheduleMode.EXACT:
        await state.set_state(Onboarding.schedule_time_select)
        await _send(callback, "Выберите удобное время.", exact_time_keyboard())
    else:
        await state.set_state(Onboarding.schedule_period_select)
        await _send(callback, "Выберите период дня.", period_keyboard())


@router.callback_query(
    F.data.startswith("sched_time:pick:"), StateFilter(Onboarding.schedule_time_select)
)
async def on_schedule_time_pick(
    callback: CallbackQuery, state: FSMContext, session: AsyncSession
) -> None:
    time_str = _cb_data(callback).split(":", 2)[2]
    await callback.answer()
    await _cb_message(callback).edit_reply_markup(reply_markup=None)
    await _finalize_exact_schedule(callback, state, session, time_str)


@router.callback_query(F.data == "sched_time:manual", StateFilter(Onboarding.schedule_time_select))
async def on_schedule_time_manual_prompt(callback: CallbackQuery, state: FSMContext) -> None:
    await callback.answer()
    await _cb_message(callback).edit_reply_markup(reply_markup=None)
    await state.set_state(Onboarding.schedule_time_manual)
    await _send(callback, "Введите время в формате ЧЧ:ММ, например 08:30.")


@router.message(StateFilter(Onboarding.schedule_time_manual), F.text)
async def on_schedule_time_manual_text(
    message: Message, state: FSMContext, session: AsyncSession
) -> None:
    await _finalize_exact_schedule(message, state, session, _text(message).strip())


async def _finalize_exact_schedule(
    event: Event, state: FSMContext, session: AsyncSession, time_str: str
) -> None:
    try:
        hour_str, minute_str = time_str.split(":")
        exact_time = time_cls(hour=int(hour_str), minute=int(minute_str))
    except (ValueError, IndexError):
        text = "Не удалось распознать время. Введите его в формате ЧЧ:ММ, например 08:30."
        await _send(event, text)
        return

    service = OnboardingService(session)
    user = await _get_user(service, event)
    if user is None:
        return
    data = await state.get_data()
    timezone_name = data.get("timezone_name")
    if timezone_name is None:
        await service.set_step(user, OnboardingStep.TIMEZONE)
        await render_timezone(event, state)
        return

    await service.finalize_schedule(
        user, timezone_name, ScheduleMode.EXACT, exact_local_time=exact_time
    )
    await state.update_data(edit_mode=False)
    await service.set_step(user, OnboardingStep.SUMMARY)
    await render_summary(event, state, service, user)


@router.callback_query(
    F.data.startswith("sched_period:"), StateFilter(Onboarding.schedule_period_select)
)
async def on_schedule_period(
    callback: CallbackQuery, state: FSMContext, session: AsyncSession
) -> None:
    period = Period(_cb_data(callback).split(":", 1)[1])
    await callback.answer()
    await _cb_message(callback).edit_reply_markup(reply_markup=None)

    service = OnboardingService(session)
    user = await _get_user(service, callback)
    if user is None:
        return
    data = await state.get_data()
    timezone_name = data.get("timezone_name")
    if timezone_name is None:
        await service.set_step(user, OnboardingStep.TIMEZONE)
        await render_timezone(callback, state)
        return

    await service.finalize_schedule(user, timezone_name, ScheduleMode.PERIOD, period=period)
    await state.update_data(edit_mode=False)
    await service.set_step(user, OnboardingStep.SUMMARY)
    await render_summary(callback, state, service, user)


# --- Резюме ---


def _format_summary(summary: OnboardingSummary) -> str:
    lines = ["Проверьте, всё ли верно:", ""]
    lines.append(
        f"Обращение: {'на «ты»' if summary.address_mode == AddressMode.INFORMAL else 'на «вы»'}"
    )

    qualities_line = ", ".join(summary.qualities) if summary.qualities else "—"
    if "qualities" in summary.custom_texts:
        qualities_line += f" (+ «{summary.custom_texts['qualities']}»)"
    lines.append(f"Качества: {qualities_line}")

    lines.append(f"Темы: {', '.join(summary.topics) if summary.topics else '—'}")

    support_line = ", ".join(summary.support_preferences) if summary.support_preferences else "—"
    if "support_preferences" in summary.custom_texts:
        support_line += f" (+ «{summary.custom_texts['support_preferences']}»)"
    lines.append(f"Способ поддержки: {support_line}")

    blocked_line = ", ".join(summary.blocked_topics) if summary.blocked_topics else "—"
    if "blocked_topics" in summary.custom_texts:
        blocked_line += f" (+ «{summary.custom_texts['blocked_topics']}»)"
    lines.append(f"Нежелательные темы: {blocked_line}")

    lines.append(f"Примеры фраз: {summary.style_examples_count}")
    lines.append(f"Часовой пояс: {summary.timezone_name or '—'}")

    if summary.schedule_mode is ScheduleMode.EXACT and summary.exact_local_time:
        lines.append(f"Время отправки: {summary.exact_local_time.strftime('%H:%M')}")
    elif summary.schedule_mode is ScheduleMode.PERIOD and summary.period:
        lines.append(f"Время отправки: {PERIOD_LABELS[summary.period]}")

    return "\n".join(lines)


async def render_summary(
    event: Event, state: FSMContext, service: OnboardingService, user: User
) -> None:
    summary = await service.build_summary(user)
    await state.set_state(Onboarding.summary)
    await _send(event, _format_summary(summary), summary_keyboard())


@router.callback_query(F.data == "summary:confirm", StateFilter(Onboarding.summary))
async def on_summary_confirm(
    callback: CallbackQuery, state: FSMContext, session: AsyncSession
) -> None:
    service = OnboardingService(session)
    user = await _get_user(service, callback)
    await callback.answer()
    await _cb_message(callback).edit_reply_markup(reply_markup=None)
    if user is None:
        return
    await service.complete_onboarding(user)
    await state.clear()
    await _cb_message(callback).answer(
        "Готово! Профиль настроен. Первое сообщение придёт по расписанию — "
        "генерация и доставка подключаются на следующих этапах разработки."
    )


@router.callback_query(F.data == "summary:edit", StateFilter(Onboarding.summary))
async def on_summary_edit(callback: CallbackQuery, state: FSMContext) -> None:
    await callback.answer()
    await _cb_message(callback).edit_reply_markup(reply_markup=None)
    await state.set_state(Onboarding.edit_menu)
    await _send(callback, "Что хотите изменить?", edit_menu_keyboard())


@router.callback_query(F.data == "edit:back", StateFilter(Onboarding.edit_menu))
async def on_edit_back(callback: CallbackQuery, state: FSMContext, session: AsyncSession) -> None:
    service = OnboardingService(session)
    user = await _get_user(service, callback)
    await callback.answer()
    await _cb_message(callback).edit_reply_markup(reply_markup=None)
    if user is None:
        return
    await render_summary(callback, state, service, user)


@router.callback_query(F.data.startswith("edit:"), StateFilter(Onboarding.edit_menu))
async def on_edit_section(
    callback: CallbackQuery, state: FSMContext, session: AsyncSession
) -> None:
    section = _cb_data(callback).split(":", 1)[1]
    service = OnboardingService(session)
    user = await _get_user(service, callback)
    await callback.answer()
    await _cb_message(callback).edit_reply_markup(reply_markup=None)
    if user is None:
        return
    await state.update_data(edit_mode=True)

    if section == "address_mode":
        await render_address_mode(callback, state)
    elif section == "qualities":
        existing = {
            str(uq.quality_id)
            for uq in await service.user_qualities.list_for_user(user.id)
            if uq.quality_id
        }
        await state.update_data(selected_quality_ids=list(existing))
        await render_qualities(callback, state, service, user)
    elif section == "topics":
        existing_topics = {
            str(ut.topic_id) for ut in await service.user_topics.list_active_for_user(user.id)
        }
        await state.update_data(selected_topic_ids=list(existing_topics))
        await render_topics(callback, state, service, user)
    elif section == "support":
        existing_support = {
            sp.preference_code
            for sp in await service.support_preferences.list_for_user(user.id)
            if sp.preference_code
        }
        await state.update_data(selected_support_codes=list(existing_support))
        await render_support(callback, state, service, user)
    elif section == "blocked":
        existing_blocked = {
            bt.topic_code
            for bt in await service.blocked_topics.list_for_user(user.id)
            if bt.topic_code
        }
        await state.update_data(selected_blocked_codes=list(existing_blocked))
        await render_blocked_topics(callback, state, service, user)
    elif section == "style_examples":
        await render_style_examples(callback, state)
    elif section == "timezone":
        await render_timezone(callback, state)


STEP_RENDERERS: dict[OnboardingStep, str] = {
    OnboardingStep.CONSENT: "consent",
    OnboardingStep.ADDRESS_MODE: "address_mode",
    OnboardingStep.QUALITIES: "qualities",
    OnboardingStep.TOPICS: "topics",
    OnboardingStep.SUPPORT_PREFERENCES: "support",
    OnboardingStep.BLOCKED_TOPICS: "blocked",
    OnboardingStep.STYLE_EXAMPLES: "style_examples",
    OnboardingStep.TIMEZONE: "timezone",
    OnboardingStep.SCHEDULE_MODE: "schedule_mode",
    OnboardingStep.SCHEDULE_TIME: "schedule_mode",
    OnboardingStep.SUMMARY: "summary",
}


async def render_current_step(
    event: Event, state: FSMContext, service: OnboardingService, user: User
) -> None:
    """Восстановление после /start: показывает промпт для незавершённого шага
    пользователя, используя персистентный `onboarding_step` из БД."""
    step = user.onboarding_step or OnboardingStep.CONSENT
    name = STEP_RENDERERS.get(step, "consent")

    if name == "consent":
        await render_consent(event, state)
    elif name == "address_mode":
        await render_address_mode(event, state)
    elif name == "qualities":
        await render_qualities(event, state, service, user)
    elif name == "topics":
        await render_topics(event, state, service, user)
    elif name == "support":
        await render_support(event, state, service, user)
    elif name == "blocked":
        await render_blocked_topics(event, state, service, user)
    elif name == "style_examples":
        await render_style_examples(event, state)
    elif name == "timezone":
        await render_timezone(event, state)
    elif name == "schedule_mode":
        await render_schedule_mode(event, state)
    elif name == "summary":
        await render_summary(event, state, service, user)


__all__ = ["router", "render_current_step"]
