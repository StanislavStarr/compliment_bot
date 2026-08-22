from aiogram import F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message
from sqlalchemy.ext.asyncio import AsyncSession

from app.application.onboarding.service import OnboardingService, OnboardingSummary
from app.application.settings.service import SettingsService
from app.domain.schedules.enums import PERIOD_LABELS, ScheduleMode
from app.domain.users.enums import AddressMode, OnboardingStep, UserStatus
from app.infrastructure.db.models.users import User
from app.infrastructure.telegram.keyboards.onboarding import edit_menu_keyboard
from app.infrastructure.telegram.keyboards.settings import (
    delete_confirm_keyboard,
    settings_keyboard,
)
from app.infrastructure.telegram.routers.admin import is_admin_telegram_id, run_admin_generation
from app.infrastructure.telegram.states.onboarding import Onboarding

router = Router(name="settings")


def _cb_message(callback: CallbackQuery) -> Message | None:
    return callback.message if isinstance(callback.message, Message) else None


def format_settings_text(summary: OnboardingSummary, status: UserStatus) -> str:
    status_label = {
        UserStatus.ACTIVE: "активен",
        UserStatus.PAUSED: "на паузе",
        UserStatus.BLOCKED: "заблокирован",
        UserStatus.ONBOARDING: "онбординг",
    }[status]
    lines = [f"Ваши настройки (статус: {status_label})", ""]
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


async def render_settings(
    event: Message | CallbackQuery, state: FSMContext, session: AsyncSession, user: User
) -> None:
    await state.clear()
    service = OnboardingService(session)
    summary = await service.build_summary(user)
    text = format_settings_text(summary, user.status)
    keyboard = settings_keyboard(
        paused=user.status is UserStatus.PAUSED,
        is_admin=is_admin_telegram_id(user.telegram_user_id),
    )
    if isinstance(event, CallbackQuery):
        target = _cb_message(event)
        if target is None:
            return
    else:
        target = event
    await target.answer(text, reply_markup=keyboard)


async def _active_user(event: Message | CallbackQuery, session: AsyncSession) -> User | None:
    from_user = event.from_user
    if from_user is None:
        return None
    user = await OnboardingService(session).users.get_by_telegram_id(from_user.id)
    if user is None or user.onboarding_step != OnboardingStep.DONE:
        if isinstance(event, CallbackQuery):
            if isinstance(event.message, Message):
                await event.message.answer("Сначала завершите настройку — отправьте /start.")
        else:
            await event.answer("Сначала завершите настройку — отправьте /start.")
        return None
    return user


@router.message(Command("settings"))
async def on_settings(message: Message, state: FSMContext, session: AsyncSession) -> None:
    user = await _active_user(message, session)
    if user is None:
        return
    await render_settings(message, state, session, user)


@router.message(Command("pause"))
async def on_pause_command(message: Message, session: AsyncSession) -> None:
    user = await _active_user(message, session)
    if user is None:
        return
    await SettingsService(session).pause(user)
    await message.answer("Сообщения приостановлены. Возобновить: /resume или /settings.")


@router.message(Command("resume"))
async def on_resume_command(message: Message, session: AsyncSession) -> None:
    user = await _active_user(message, session)
    if user is None:
        return
    await SettingsService(session).resume(user)
    await message.answer("Расписание снова активно. Следующее сообщение придёт в выбранное время.")


@router.message(Command("delete"))
async def on_delete_command(message: Message) -> None:
    await message.answer(
        "Удалить профиль и все связанные данные без возможности восстановления?",
        reply_markup=delete_confirm_keyboard(),
    )


@router.callback_query(F.data == "settings:edit")
async def on_settings_edit(callback: CallbackQuery, state: FSMContext) -> None:
    await callback.answer()
    await state.update_data(settings_edit=True)
    await state.set_state(Onboarding.edit_menu)
    msg = _cb_message(callback)
    if msg is not None:
        await msg.edit_reply_markup(reply_markup=None)
        await msg.answer(
            "Что хотите изменить?",
            reply_markup=edit_menu_keyboard(
                back_callback="settings:back", back_text="⬅️ Назад к настройкам"
            ),
        )


@router.callback_query(F.data == "settings:back")
async def on_settings_back(
    callback: CallbackQuery, state: FSMContext, session: AsyncSession
) -> None:
    user = await _active_user(callback, session)
    await callback.answer()
    msg = _cb_message(callback)
    if msg is not None:
        await msg.edit_reply_markup(reply_markup=None)
    if user is None:
        return
    await render_settings(callback, state, session, user)


@router.callback_query(F.data == "settings:pause")
async def on_settings_pause(
    callback: CallbackQuery, state: FSMContext, session: AsyncSession
) -> None:
    user = await _active_user(callback, session)
    await callback.answer()
    if user is None:
        return
    await SettingsService(session).pause(user)
    user.status = UserStatus.PAUSED
    msg = _cb_message(callback)
    if msg is not None:
        await msg.edit_reply_markup(reply_markup=None)
    await render_settings(callback, state, session, user)


@router.callback_query(F.data == "settings:resume")
async def on_settings_resume(
    callback: CallbackQuery, state: FSMContext, session: AsyncSession
) -> None:
    user = await _active_user(callback, session)
    await callback.answer()
    if user is None:
        return
    await SettingsService(session).resume(user)
    user.status = UserStatus.ACTIVE
    msg = _cb_message(callback)
    if msg is not None:
        await msg.edit_reply_markup(reply_markup=None)
    await render_settings(callback, state, session, user)


@router.callback_query(F.data == "settings:info")
async def on_settings_info(callback: CallbackQuery) -> None:
    await callback.answer()
    msg = _cb_message(callback)
    if msg is not None:
        await msg.answer(
            "Раз в день присылаю короткий комплимент или слова поддержки по вашему "
            "профилю. Сообщения генерирует AI. Данные не передаются третьим лицам. "
            "Управление: /settings, пауза — /pause, удаление — /delete."
        )


@router.callback_query(F.data == "settings:generate")
async def on_settings_generate(callback: CallbackQuery, session: AsyncSession) -> None:
    await callback.answer()
    if callback.from_user is None or not is_admin_telegram_id(callback.from_user.id):
        return
    msg = _cb_message(callback)
    if msg is not None:
        await run_admin_generation(msg, session, callback.from_user.id)


@router.callback_query(F.data == "settings:delete")
async def on_settings_delete(callback: CallbackQuery) -> None:
    await callback.answer()
    msg = _cb_message(callback)
    if msg is not None:
        await msg.answer(
            "Удалить профиль и все связанные данные без возможности восстановления?",
            reply_markup=delete_confirm_keyboard(),
        )


@router.callback_query(F.data == "settings:delete_cancel")
async def on_settings_delete_cancel(callback: CallbackQuery) -> None:
    await callback.answer("Отменено")
    msg = _cb_message(callback)
    if msg is not None:
        await msg.edit_reply_markup(reply_markup=None)


@router.callback_query(F.data == "settings:delete_confirm")
async def on_settings_delete_confirm(callback: CallbackQuery, session: AsyncSession) -> None:
    user = await _active_user(callback, session)
    await callback.answer()
    if user is None:
        return
    await SettingsService(session).delete_account(user)
    msg = _cb_message(callback)
    if msg is not None:
        await msg.edit_reply_markup(reply_markup=None)
        await msg.answer("Профиль удалён. Если захотите начать снова — /start.")
