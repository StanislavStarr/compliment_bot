import uuid

from aiogram import F, Router
from aiogram.filters import StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message
from sqlalchemy.ext.asyncio import AsyncSession

from app.application.author_onboarding.service import AuthorOnboardingService
from app.domain.profiles.constants import SUPPORT_PREFERENCE_OPTIONS
from app.domain.topics.enums import MAX_ACTIVE_TOPICS_PER_USER
from app.domain.users.enums import AddressMode
from app.infrastructure.telegram.helpers import Event, cb_data, cb_message, message_text, send
from app.infrastructure.telegram.keyboards.author import address_mode_keyboard
from app.infrastructure.telegram.keyboards.common import multi_select_keyboard, skip_keyboard
from app.infrastructure.telegram.routers.author.common import (
    MAX_STYLE_EXAMPLES,
    finish_section,
    get_author,
)
from app.infrastructure.telegram.states.author import AuthorOnboarding

router = Router(name="author_portrait")


async def render_address_mode(event: Event, state: FSMContext) -> None:
    await state.set_state(AuthorOnboarding.address_mode)
    await send(event, "Как боту обращаться к этому человеку?", address_mode_keyboard())


@router.callback_query(F.data.startswith("addr:"), StateFilter(AuthorOnboarding.address_mode))
async def on_address_mode(
    callback: CallbackQuery, state: FSMContext, session: AsyncSession
) -> None:
    service = AuthorOnboardingService(session)
    user = await get_author(service, callback)
    await callback.answer()
    if user is None:
        return
    mode = AddressMode(cb_data(callback).split(":", 1)[1])
    await service.save_address_mode(user, mode)
    await cb_message(callback).edit_reply_markup(reply_markup=None)
    await finish_section(callback, state, session, user)


async def render_qualities(
    event: Event, state: FSMContext, service: AuthorOnboardingService
) -> None:
    data = await state.get_data()
    selected = set(data.get("selected_quality_ids", []))
    qualities = await service.list_qualities()
    options = [(str(q.id), q.label) for q in qualities]
    await state.update_data(selected_quality_ids=list(selected))
    await state.set_state(AuthorOnboarding.qualities_select)
    await send(
        event,
        "Какие качества характера у этого человека? Можно выбрать несколько.",
        multi_select_keyboard(options, selected, prefix="qual"),
    )


@router.callback_query(
    F.data.startswith("qual:toggle:"), StateFilter(AuthorOnboarding.qualities_select)
)
async def on_quality_toggle(
    callback: CallbackQuery, state: FSMContext, session: AsyncSession
) -> None:
    service = AuthorOnboardingService(session)
    quality_id = cb_data(callback).split(":", 2)[2]
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
    await cb_message(callback).edit_reply_markup(
        reply_markup=multi_select_keyboard(options, selected, prefix="qual")
    )


@router.callback_query(F.data == "qual:done", StateFilter(AuthorOnboarding.qualities_select))
async def on_qualities_done(callback: CallbackQuery, state: FSMContext) -> None:
    await callback.answer()
    await cb_message(callback).edit_reply_markup(reply_markup=None)
    await state.set_state(AuthorOnboarding.qualities_custom)
    await send(
        callback,
        "Хотите добавить своими словами ещё черты этого человека? "
        "Напишите текстом или нажмите «Пропустить».",
        skip_keyboard("qual:skip"),
    )


async def _save_qualities(
    event: Event, state: FSMContext, session: AsyncSession, custom_text: str | None
) -> None:
    service = AuthorOnboardingService(session)
    user = await get_author(service, event)
    if user is None:
        return
    data = await state.get_data()
    quality_ids = [uuid.UUID(x) for x in data.get("selected_quality_ids", [])]
    await service.save_qualities(user, quality_ids, custom_text, is_sensitive=False)
    await state.update_data(selected_quality_ids=[])
    await finish_section(event, state, session, user)


@router.message(StateFilter(AuthorOnboarding.qualities_custom), F.text)
async def on_qualities_custom_text(
    message: Message, state: FSMContext, session: AsyncSession
) -> None:
    await _save_qualities(message, state, session, message_text(message).strip())


@router.callback_query(F.data == "qual:skip", StateFilter(AuthorOnboarding.qualities_custom))
async def on_qualities_custom_skip(
    callback: CallbackQuery, state: FSMContext, session: AsyncSession
) -> None:
    await callback.answer()
    await cb_message(callback).edit_reply_markup(reply_markup=None)
    await _save_qualities(callback, state, session, None)


async def render_topics(event: Event, state: FSMContext, service: AuthorOnboardingService) -> None:
    data = await state.get_data()
    selected = set(data.get("selected_topic_ids", []))
    topics = await service.list_topics()
    options = [(str(t.id), t.label) for t in topics]
    await state.update_data(selected_topic_ids=list(selected))
    await state.set_state(AuthorOnboarding.topics_select)
    await send(
        event,
        f"Выберите до {MAX_ACTIVE_TOPICS_PER_USER} тем для сообщений этому человеку.",
        multi_select_keyboard(options, selected, prefix="topic"),
    )


@router.callback_query(
    F.data.startswith("topic:toggle:"), StateFilter(AuthorOnboarding.topics_select)
)
async def on_topic_toggle(
    callback: CallbackQuery, state: FSMContext, session: AsyncSession
) -> None:
    service = AuthorOnboardingService(session)
    topic_id = cb_data(callback).split(":", 2)[2]
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
    await cb_message(callback).edit_reply_markup(
        reply_markup=multi_select_keyboard(options, selected, prefix="topic")
    )


@router.callback_query(F.data == "topic:done", StateFilter(AuthorOnboarding.topics_select))
async def on_topics_done(callback: CallbackQuery, state: FSMContext, session: AsyncSession) -> None:
    service = AuthorOnboardingService(session)
    user = await get_author(service, callback)
    await callback.answer()
    await cb_message(callback).edit_reply_markup(reply_markup=None)
    if user is None:
        return
    data = await state.get_data()
    topic_ids = [uuid.UUID(x) for x in data.get("selected_topic_ids", [])]
    await service.save_topics(user, topic_ids)
    await state.update_data(selected_topic_ids=[])
    await finish_section(callback, state, session, user)


async def render_support(event: Event, state: FSMContext) -> None:
    data = await state.get_data()
    selected = set(data.get("selected_support_codes", []))
    await state.update_data(selected_support_codes=list(selected))
    await state.set_state(AuthorOnboarding.support_select)
    await send(
        event,
        "Что обычно помогает этому человеку почувствовать поддержку? Можно выбрать несколько.",
        multi_select_keyboard(SUPPORT_PREFERENCE_OPTIONS, selected, prefix="supp"),
    )


@router.callback_query(
    F.data.startswith("supp:toggle:"), StateFilter(AuthorOnboarding.support_select)
)
async def on_support_toggle(callback: CallbackQuery, state: FSMContext) -> None:
    code = cb_data(callback).split(":", 2)[2]
    data = await state.get_data()
    selected = set(data.get("selected_support_codes", []))
    if code in selected:
        selected.discard(code)
    else:
        selected.add(code)
    await state.update_data(selected_support_codes=list(selected))
    await callback.answer()
    await cb_message(callback).edit_reply_markup(
        reply_markup=multi_select_keyboard(SUPPORT_PREFERENCE_OPTIONS, selected, prefix="supp")
    )


@router.callback_query(F.data == "supp:done", StateFilter(AuthorOnboarding.support_select))
async def on_support_done(callback: CallbackQuery, state: FSMContext) -> None:
    await callback.answer()
    await cb_message(callback).edit_reply_markup(reply_markup=None)
    await state.set_state(AuthorOnboarding.support_custom)
    await send(
        callback,
        "Хотите уточнить своими словами, что помогает этому человеку? "
        "Напишите текстом или нажмите «Пропустить».",
        skip_keyboard("supp:skip"),
    )


async def _save_support(
    event: Event, state: FSMContext, session: AsyncSession, custom_text: str | None
) -> None:
    service = AuthorOnboardingService(session)
    user = await get_author(service, event)
    if user is None:
        return
    data = await state.get_data()
    codes = list(data.get("selected_support_codes", []))
    await service.save_support_preferences(user, codes, custom_text, is_sensitive=False)
    await state.update_data(selected_support_codes=[])
    await finish_section(event, state, session, user)


@router.message(StateFilter(AuthorOnboarding.support_custom), F.text)
async def on_support_custom_text(
    message: Message, state: FSMContext, session: AsyncSession
) -> None:
    await _save_support(message, state, session, message_text(message).strip())


@router.callback_query(F.data == "supp:skip", StateFilter(AuthorOnboarding.support_custom))
async def on_support_custom_skip(
    callback: CallbackQuery, state: FSMContext, session: AsyncSession
) -> None:
    await callback.answer()
    await cb_message(callback).edit_reply_markup(reply_markup=None)
    await _save_support(callback, state, session, None)


async def render_blocked(event: Event, state: FSMContext, service: AuthorOnboardingService) -> None:
    data = await state.get_data()
    selected = set(data.get("selected_blocked_codes", []))
    topics = await service.list_topics()
    options = [(t.code, t.label) for t in topics]
    await state.update_data(selected_blocked_codes=list(selected))
    await state.set_state(AuthorOnboarding.blocked_select)
    await send(
        event,
        "Есть темы, которые лучше не затрагивать в сообщениях для этого человека?",
        multi_select_keyboard(options, selected, prefix="block"),
    )


@router.callback_query(
    F.data.startswith("block:toggle:"), StateFilter(AuthorOnboarding.blocked_select)
)
async def on_blocked_toggle(
    callback: CallbackQuery, state: FSMContext, session: AsyncSession
) -> None:
    service = AuthorOnboardingService(session)
    code = cb_data(callback).split(":", 2)[2]
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
    await cb_message(callback).edit_reply_markup(
        reply_markup=multi_select_keyboard(options, selected, prefix="block")
    )


@router.callback_query(F.data == "block:done", StateFilter(AuthorOnboarding.blocked_select))
async def on_blocked_done(callback: CallbackQuery, state: FSMContext) -> None:
    await callback.answer()
    await cb_message(callback).edit_reply_markup(reply_markup=None)
    await state.set_state(AuthorOnboarding.blocked_custom)
    await send(
        callback,
        "Хотите уточнить своими словами, чего лучше избегать? "
        "Напишите текстом или нажмите «Пропустить».",
        skip_keyboard("block:skip"),
    )


async def _save_blocked(
    event: Event, state: FSMContext, session: AsyncSession, custom_text: str | None
) -> None:
    service = AuthorOnboardingService(session)
    user = await get_author(service, event)
    if user is None:
        return
    data = await state.get_data()
    codes = list(data.get("selected_blocked_codes", []))
    await service.save_blocked_topics(user, codes, custom_text, is_sensitive=False)
    await state.update_data(selected_blocked_codes=[])
    await finish_section(event, state, session, user)


@router.message(StateFilter(AuthorOnboarding.blocked_custom), F.text)
async def on_blocked_custom_text(
    message: Message, state: FSMContext, session: AsyncSession
) -> None:
    await _save_blocked(message, state, session, message_text(message).strip())


@router.callback_query(F.data == "block:skip", StateFilter(AuthorOnboarding.blocked_custom))
async def on_blocked_custom_skip(
    callback: CallbackQuery, state: FSMContext, session: AsyncSession
) -> None:
    await callback.answer()
    await cb_message(callback).edit_reply_markup(reply_markup=None)
    await _save_blocked(callback, state, session, None)


async def render_style_examples(event: Event, state: FSMContext) -> None:
    await state.update_data(style_examples_count=0)
    await state.set_state(AuthorOnboarding.style_examples)
    await send(
        event,
        f"Необязательно: пришлите 1–{MAX_STYLE_EXAMPLES} примера фраз, которые подошли бы "
        "этому человеку (по одной сообщением). Когда закончите — нажмите «Готово».",
        skip_keyboard("style:done", text="Готово / Пропустить"),
    )


@router.message(StateFilter(AuthorOnboarding.style_examples), F.text)
async def on_style_example_text(message: Message, state: FSMContext, session: AsyncSession) -> None:
    service = AuthorOnboardingService(session)
    user = await get_author(service, message)
    if user is None:
        return
    await service.add_style_example(user, message_text(message).strip())
    data = await state.get_data()
    count = int(data.get("style_examples_count", 0)) + 1
    await state.update_data(style_examples_count=count)
    if count >= MAX_STYLE_EXAMPLES:
        await finish_section(message, state, session, user)
        return
    await message.answer(
        f"Записал! Можно добавить ещё ({MAX_STYLE_EXAMPLES - count}) или нажать «Готово».",
        reply_markup=skip_keyboard("style:done", text="Готово / Пропустить"),
    )


@router.callback_query(F.data == "style:done", StateFilter(AuthorOnboarding.style_examples))
async def on_style_examples_done(
    callback: CallbackQuery, state: FSMContext, session: AsyncSession
) -> None:
    service = AuthorOnboardingService(session)
    user = await get_author(service, callback)
    await callback.answer()
    await cb_message(callback).edit_reply_markup(reply_markup=None)
    if user is None:
        return
    await finish_section(callback, state, session, user)


async def render_portrait_notes(event: Event, state: FSMContext) -> None:
    await state.set_state(AuthorOnboarding.portrait_notes)
    await send(
        event,
        "Опишите человека своими словами — характер, как он проявляет себя, "
        "что для него важно. Или нажмите «Пропустить».",
        skip_keyboard("portrait:skip"),
    )


@router.message(StateFilter(AuthorOnboarding.portrait_notes), F.text)
async def on_portrait_notes_text(
    message: Message, state: FSMContext, session: AsyncSession
) -> None:
    service = AuthorOnboardingService(session)
    user = await get_author(service, message)
    if user is None:
        return
    await service.save_portrait_notes(user, message_text(message))
    await finish_section(message, state, session, user)


@router.callback_query(F.data == "portrait:skip", StateFilter(AuthorOnboarding.portrait_notes))
async def on_portrait_notes_skip(
    callback: CallbackQuery, state: FSMContext, session: AsyncSession
) -> None:
    service = AuthorOnboardingService(session)
    user = await get_author(service, callback)
    await callback.answer()
    await cb_message(callback).edit_reply_markup(reply_markup=None)
    if user is None:
        return
    await service.save_portrait_notes(user, None)
    await finish_section(callback, state, session, user)
