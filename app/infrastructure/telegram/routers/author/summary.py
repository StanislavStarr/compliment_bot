from aiogram import F, Router
from aiogram.filters import StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery
from sqlalchemy.ext.asyncio import AsyncSession

from app.application.author_onboarding.service import (
    AuthorOnboardingError,
    AuthorOnboardingService,
    AuthorOnboardingSummary,
)
from app.application.invites.service import InviteError
from app.domain.messages.enums import MessageType
from app.domain.orders.enums import InviteStatus, OrderStatus
from app.domain.users.enums import AddressMode
from app.infrastructure.db.repositories.schedules import ScheduleRepository
from app.infrastructure.telegram.helpers import Event, bot_username, cb_data, cb_message, send
from app.infrastructure.telegram.keyboards.author import author_edit_menu_keyboard, summary_keyboard
from app.infrastructure.telegram.keyboards.settings import (
    author_home_keyboard,
    stopped_profile_keyboard,
)
from app.infrastructure.telegram.routers.author.common import get_author
from app.infrastructure.telegram.states.author import AuthorOnboarding

router = Router(name="author_summary")


def format_author_summary(summary: AuthorOnboardingSummary) -> str:
    genre = "—"
    if summary.message_type is MessageType.COMPLIMENT:
        genre = "короткие комплименты"
    elif summary.message_type is MessageType.SUPPORT:
        genre = "слова поддержки"
    address = "—"
    if summary.address_mode is AddressMode.INFORMAL:
        address = "на «ты»"
    elif summary.address_mode is AddressMode.FORMAL:
        address = "на «вы»"
    nick = f"@{summary.recipient_username}" if summary.recipient_username else "—"
    qualities = ", ".join(summary.qualities) if summary.qualities else "—"
    if "qualities" in summary.custom_texts:
        qualities += f" (+ «{summary.custom_texts['qualities']}»)"
    support = ", ".join(summary.support_preferences) if summary.support_preferences else "—"
    if "support_preferences" in summary.custom_texts:
        support += f" (+ «{summary.custom_texts['support_preferences']}»)"
    blocked = ", ".join(summary.blocked_topics) if summary.blocked_topics else "—"
    if "blocked_topics" in summary.custom_texts:
        blocked += f" (+ «{summary.custom_texts['blocked_topics']}»)"
    lines = [
        "Проверьте заказ:",
        "",
        f"Тип сообщений: {genre}",
        f"Адресат: {nick}",
        f"Обращение: {address}",
        f"Качества: {qualities}",
        f"Темы: {', '.join(summary.topics) if summary.topics else '—'}",
    ]
    if summary.message_type is MessageType.SUPPORT:
        lines.append(f"Способ поддержки: {support}")
    lines.append(f"Нежелательные темы: {blocked}")
    lines.append(f"Примеры фраз: {summary.style_examples_count}")
    lines.append(f"Портрет: {summary.portrait_notes or '—'}")
    return "\n".join(lines)


async def render_summary(
    event: Event, state: FSMContext, service: AuthorOnboardingService, user: object
) -> None:
    from app.infrastructure.db.models.users import User

    assert isinstance(user, User)
    summary = await service.build_summary(user)
    await state.set_state(AuthorOnboarding.summary)
    await send(event, format_author_summary(summary), summary_keyboard())


async def render_author_home(
    event: Event, state: FSMContext, session: AsyncSession, user: object
) -> None:
    from app.infrastructure.db.models.users import User

    assert isinstance(user, User)
    await state.clear()
    service = AuthorOnboardingService(session)
    order = await service.orders.get_open_for_author(user)
    if order is None:
        await send(
            event,
            "Открытого заказа нет. Нажмите /start, чтобы создать новый.",
            stopped_profile_keyboard(),
        )
        return
    username = await bot_username(event)
    keyboard = author_home_keyboard(cancellable=True)
    if order.status is OrderStatus.PENDING:
        invite = await service.invites.invites.get_by_order_id(order.id)
        if invite is not None and invite.status is InviteStatus.ACCEPTED:
            await send(
                event,
                f"@{order.recipient_username} уже открыл ссылку и настраивает время получения.",
                keyboard,
            )
            return
        issued = await service.invites.issue(order, username)
        await send(
            event,
            "Заказ создан. Отправьте эту ссылку адресату — открыть её сможет только "
            f"@{order.recipient_username}.\n\n{issued.link}\n\n"
            "Когда человек примет приглашение, сообщения пойдут ему по выбранному времени.",
            keyboard,
        )
        return
    if order.status is OrderStatus.ACTIVE:
        paused_note = ""
        if order.recipient_user_id is not None:
            schedule = await ScheduleRepository(session).get_by_user_id(order.recipient_user_id)
            if schedule is not None and not schedule.is_active:
                paused_note = "\nСейчас доставка на паузе."
        await send(
            event,
            f"@{order.recipient_username} уже получает сообщения по этому заказу.{paused_note}",
            keyboard,
        )
        return
    await send(event, "Заказ ещё заполняется. Нажмите /start, чтобы продолжить анкету.", keyboard)


@router.callback_query(F.data == "summary:confirm", StateFilter(AuthorOnboarding.summary))
async def on_summary_confirm(
    callback: CallbackQuery, state: FSMContext, session: AsyncSession
) -> None:
    service = AuthorOnboardingService(session)
    user = await get_author(service, callback)
    await callback.answer()
    await cb_message(callback).edit_reply_markup(reply_markup=None)
    if user is None:
        return
    if callback.from_user is None or callback.from_user.username is None:
        await send(
            callback,
            "Укажите username в настройках Telegram и снова нажмите /start — "
            "без @ника адресат не увидит, кто заказал сообщения.",
        )
        return
    try:
        issued = await service.issue_invite(user, await bot_username(callback))
    except (AuthorOnboardingError, InviteError) as exc:
        await send(callback, f"Не удалось создать ссылку: {exc}")
        return
    await state.clear()
    order = await service.draft_order(user)
    await send(
        callback,
        "Готово. Отправьте ссылку адресату — она персональная, "
        f"открыть сможет только @{order.recipient_username}.\n\n{issued.link}",
    )


@router.callback_query(F.data == "summary:edit", StateFilter(AuthorOnboarding.summary))
async def on_summary_edit(
    callback: CallbackQuery, state: FSMContext, session: AsyncSession
) -> None:
    service = AuthorOnboardingService(session)
    user = await get_author(service, callback)
    await callback.answer()
    await cb_message(callback).edit_reply_markup(reply_markup=None)
    if user is None:
        return
    order = await service.draft_order(user)
    await state.set_state(AuthorOnboarding.edit_menu)
    await send(
        callback,
        "Что хотите изменить?",
        author_edit_menu_keyboard(include_support=order.message_type is MessageType.SUPPORT),
    )


@router.callback_query(F.data == "edit:back", StateFilter(AuthorOnboarding.edit_menu))
async def on_edit_back(callback: CallbackQuery, state: FSMContext, session: AsyncSession) -> None:
    service = AuthorOnboardingService(session)
    user = await get_author(service, callback)
    await callback.answer()
    await cb_message(callback).edit_reply_markup(reply_markup=None)
    if user is None:
        return
    await render_summary(callback, state, service, user)


@router.callback_query(F.data.startswith("edit:"), StateFilter(AuthorOnboarding.edit_menu))
async def on_edit_section(
    callback: CallbackQuery, state: FSMContext, session: AsyncSession
) -> None:
    from app.infrastructure.telegram.routers.author.genre import render_genre
    from app.infrastructure.telegram.routers.author.portrait import (
        render_address_mode,
        render_blocked,
        render_portrait_notes,
        render_qualities,
        render_style_examples,
        render_support,
        render_topics,
    )
    from app.infrastructure.telegram.routers.author.recipient import render_recipient_username

    section = cb_data(callback).split(":", 1)[1]
    service = AuthorOnboardingService(session)
    user = await get_author(service, callback)
    await callback.answer()
    await cb_message(callback).edit_reply_markup(reply_markup=None)
    if user is None:
        return
    await state.update_data(edit_mode=True)
    order = await service.draft_order(user)

    if section == "genre":
        await render_genre(callback, state)
    elif section == "recipient":
        await render_recipient_username(callback, state)
    elif section == "address_mode":
        await render_address_mode(callback, state)
    elif section == "qualities":
        existing = {
            str(uq.quality_id)
            for uq in await service.order_qualities.list_for_order(order.id)
            if uq.quality_id
        }
        await state.update_data(selected_quality_ids=list(existing))
        await render_qualities(callback, state, service)
    elif section == "topics":
        existing = {
            str(ut.topic_id) for ut in await service.order_topics.list_active_for_order(order.id)
        }
        await state.update_data(selected_topic_ids=list(existing))
        await render_topics(callback, state, service)
    elif section == "support":
        existing = {
            sp.preference_code
            for sp in await service.support_preferences.list_for_order(order.id)
            if sp.preference_code
        }
        await state.update_data(selected_support_codes=list(existing))
        await render_support(callback, state)
    elif section == "blocked":
        existing = {
            bt.topic_code
            for bt in await service.blocked_topics.list_for_order(order.id)
            if bt.topic_code
        }
        await state.update_data(selected_blocked_codes=list(existing))
        await render_blocked(callback, state, service)
    elif section == "style_examples":
        await render_style_examples(callback, state)
    elif section == "portrait_notes":
        await render_portrait_notes(callback, state)
