from aiogram import F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message
from sqlalchemy.ext.asyncio import AsyncSession

from app.application.orders.notices import NoticeKind
from app.application.orders.service import OrderService
from app.application.settings.service import SettingsService
from app.domain.users.enums import AuthorOnboardingStep, RecipientOnboardingStep, UserRole
from app.infrastructure.db.models.users import User
from app.infrastructure.db.repositories.users import UserRepository
from app.infrastructure.telegram.helpers import (
    Event,
    cb_message,
    clear_markup,
    send,
    telegram_user_id,
)
from app.infrastructure.telegram.keyboards.settings import (
    confirm_action_keyboard,
    delete_confirm_keyboard,
)
from app.infrastructure.telegram.notices import deliver_counterpart_notice
from app.infrastructure.telegram.routers.admin import is_admin_telegram_id, run_admin_generation
from app.infrastructure.telegram.routers.author import render_author_home
from app.infrastructure.telegram.routers.recipient.home import render_recipient_home
from app.infrastructure.telegram.routers.recipient.schedule import render_timezone

router = Router(name="settings")

_NOT_READY = "Сначала завершите настройку — отправьте /start."
_AUTHOR_NO_SCHEDULE = "Приостановить может адресат. Отменить заказ: /settings."


async def render_settings(
    event: Event, state: FSMContext, session: AsyncSession, user: User
) -> None:
    if user.role is UserRole.RECIPIENT:
        await render_recipient_home(event, state, session, user)
        return
    await render_author_home(event, state, session, user)


async def _settings_user(event: Event, session: AsyncSession) -> User | None:
    try:
        user_id = telegram_user_id(event)
    except AssertionError:
        return None
    user = await UserRepository(session).get_by_telegram_id(user_id)
    if user is None or not _ready_for_settings(user):
        await send(event, _NOT_READY)
        return None
    return user


def _ready_for_settings(user: User) -> bool:
    if user.role is UserRole.RECIPIENT:
        return user.recipient_step is RecipientOnboardingStep.DONE
    return user.author_step is AuthorOnboardingStep.DONE


@router.message(Command("settings"))
async def on_settings(message: Message, state: FSMContext, session: AsyncSession) -> None:
    user = await _settings_user(message, session)
    if user is None:
        return
    await render_settings(message, state, session, user)


@router.message(Command("pause"))
async def on_pause_command(message: Message, session: AsyncSession) -> None:
    user = await _settings_user(message, session)
    if user is None:
        return
    if user.role is not UserRole.RECIPIENT:
        await message.answer(_AUTHOR_NO_SCHEDULE)
        return
    await SettingsService(session).pause(user)
    await message.answer("Сообщения приостановлены. Возобновить: /resume или /settings.")


@router.message(Command("resume"))
async def on_resume_command(message: Message, session: AsyncSession) -> None:
    user = await _settings_user(message, session)
    if user is None:
        return
    if user.role is not UserRole.RECIPIENT:
        await message.answer(_AUTHOR_NO_SCHEDULE)
        return
    await SettingsService(session).resume(user)
    await message.answer("Расписание снова активно. Следующее сообщение придёт в выбранное время.")


@router.message(Command("delete"))
async def on_delete_command(message: Message) -> None:
    await message.answer(
        "Удалить профиль и все связанные данные без возможности восстановления?",
        reply_markup=delete_confirm_keyboard(),
    )


@router.callback_query(F.data == "settings:back")
async def on_settings_back(
    callback: CallbackQuery, state: FSMContext, session: AsyncSession
) -> None:
    user = await _settings_user(callback, session)
    await callback.answer()
    await clear_markup(callback)
    if user is None:
        return
    await render_settings(callback, state, session, user)


@router.callback_query(F.data == "settings:pause")
async def on_settings_pause(
    callback: CallbackQuery, state: FSMContext, session: AsyncSession
) -> None:
    user = await _settings_user(callback, session)
    await callback.answer()
    await clear_markup(callback)
    if user is None or user.role is not UserRole.RECIPIENT:
        return
    await SettingsService(session).pause(user)
    await render_recipient_home(callback, state, session, user)


@router.callback_query(F.data == "settings:resume")
async def on_settings_resume(
    callback: CallbackQuery, state: FSMContext, session: AsyncSession
) -> None:
    user = await _settings_user(callback, session)
    await callback.answer()
    await clear_markup(callback)
    if user is None or user.role is not UserRole.RECIPIENT:
        return
    await SettingsService(session).resume(user)
    await render_recipient_home(callback, state, session, user)


@router.callback_query(F.data == "settings:slot")
async def on_settings_slot(
    callback: CallbackQuery, state: FSMContext, session: AsyncSession
) -> None:
    user = await _settings_user(callback, session)
    await callback.answer()
    await clear_markup(callback)
    if user is None or user.role is not UserRole.RECIPIENT:
        return
    order = await OrderService(session).get_open_for_recipient(user)
    if order is None:
        await send(callback, "Открытого заказа нет.")
        return
    await state.update_data(settings_edit=True, order_id=str(order.id))
    await render_timezone(callback, state)


@router.callback_query(F.data == "order:cancel")
async def on_order_cancel_prompt(callback: CallbackQuery, session: AsyncSession) -> None:
    user = await _settings_user(callback, session)
    await callback.answer()
    await clear_markup(callback)
    if user is None:
        return
    await send(
        callback,
        "Отменить заказ? Адресат перестанет получать сообщения.",
        confirm_action_keyboard(yes="order:cancel_confirm", no="order:cancel_abort"),
    )


@router.callback_query(F.data == "order:cancel_abort")
async def on_order_cancel_abort(
    callback: CallbackQuery, state: FSMContext, session: AsyncSession
) -> None:
    user = await _settings_user(callback, session)
    await callback.answer()
    await clear_markup(callback)
    if user is None:
        return
    await render_settings(callback, state, session, user)


@router.callback_query(F.data == "order:cancel_confirm")
async def on_order_cancel_confirm(callback: CallbackQuery, session: AsyncSession) -> None:
    user = await _settings_user(callback, session)
    await callback.answer()
    await clear_markup(callback)
    if user is None:
        return
    orders = OrderService(session)
    order = await orders.get_open_for_author(user)
    if order is None:
        await send(callback, "Открытого заказа нет. Новый заказ — /start.")
        return
    notice = await orders.cancel(order, initiated_by=NoticeKind.AUTHOR_CANCELLED)
    await send(callback, "Заказ отменён. Новый заказ — /start.")
    if notice is not None and callback.bot is not None:
        await deliver_counterpart_notice(callback.bot, notice)


@router.callback_query(F.data == "order:stop")
async def on_order_stop_prompt(callback: CallbackQuery, session: AsyncSession) -> None:
    user = await _settings_user(callback, session)
    await callback.answer()
    await clear_markup(callback)
    if user is None:
        return
    await send(
        callback,
        "Остановить получение? Заказчик получит уведомление, сообщения прекратятся.",
        confirm_action_keyboard(yes="order:stop_confirm", no="order:stop_abort"),
    )


@router.callback_query(F.data == "order:stop_abort")
async def on_order_stop_abort(
    callback: CallbackQuery, state: FSMContext, session: AsyncSession
) -> None:
    user = await _settings_user(callback, session)
    await callback.answer()
    await clear_markup(callback)
    if user is None:
        return
    await render_settings(callback, state, session, user)


@router.callback_query(F.data == "order:stop_confirm")
async def on_order_stop_confirm(callback: CallbackQuery, session: AsyncSession) -> None:
    user = await _settings_user(callback, session)
    await callback.answer()
    await clear_markup(callback)
    if user is None:
        return
    orders = OrderService(session)
    order = await orders.get_open_for_recipient(user)
    if order is None:
        await send(callback, "Открытого заказа нет.")
        return
    notice = await orders.cancel(order, initiated_by=NoticeKind.RECIPIENT_STOPPED)
    await send(callback, "Получение остановлено. Новый заказ — только по новой ссылке.")
    if notice is not None and callback.bot is not None:
        await deliver_counterpart_notice(callback.bot, notice)


@router.callback_query(F.data == "settings:info")
async def on_settings_info(callback: CallbackQuery) -> None:
    await callback.answer()
    await send(
        callback,
        "Раз в день адресат получает короткий комплимент или слова поддержки по заказу. "
        "Сообщения генерирует AI. Данные не передаются третьим лицам.\n\n"
        "Заказчик может отменить заказ в /settings. Адресат может поставить паузу "
        "или остановить получение.",
    )


@router.callback_query(F.data == "settings:generate")
async def on_settings_generate(callback: CallbackQuery, session: AsyncSession) -> None:
    await callback.answer()
    if callback.from_user is None or not is_admin_telegram_id(callback.from_user.id):
        return
    await run_admin_generation(cb_message(callback), session, callback.from_user.id)


@router.callback_query(F.data == "settings:delete")
async def on_settings_delete(callback: CallbackQuery) -> None:
    await callback.answer()
    await send(
        callback,
        "Удалить профиль и все связанные данные без возможности восстановления?",
        delete_confirm_keyboard(),
    )


@router.callback_query(F.data == "settings:delete_cancel")
async def on_settings_delete_cancel(callback: CallbackQuery) -> None:
    await callback.answer("Отменено")
    await clear_markup(callback)


@router.callback_query(F.data == "settings:delete_confirm")
async def on_settings_delete_confirm(callback: CallbackQuery, session: AsyncSession) -> None:
    user = await _settings_user(callback, session)
    await callback.answer()
    await clear_markup(callback)
    if user is None:
        return
    notice = await SettingsService(session).delete_account(user)
    await send(callback, "Профиль удалён. Если захотите начать снова — /start.")
    if notice is not None and callback.bot is not None:
        await deliver_counterpart_notice(callback.bot, notice)
