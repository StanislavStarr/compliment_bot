"""Служебные команды для проверки внутренней механики бота. Не часть
продуктового сценария — доступны только `ADMIN_TELEGRAM_ID` из настроек."""

import html

from aiogram import Router
from aiogram.exceptions import TelegramAPIError
from aiogram.filters import Command
from aiogram.types import Message
from sqlalchemy.ext.asyncio import AsyncSession

from app.application.admin.service import ManualDeliveryError, ManualDeliveryService
from app.config import get_settings
from app.domain.users.enums import UserStatus
from app.infrastructure.ai.factory import create_ai_provider
from app.infrastructure.db.repositories.users import UserRepository
from app.infrastructure.telegram.keyboards.feedback import feedback_keyboard

router = Router(name="admin")


def is_admin_telegram_id(telegram_user_id: int) -> bool:
    settings = get_settings()
    return settings.admin_telegram_id is not None and telegram_user_id == settings.admin_telegram_id


async def run_admin_generation(
    reply_target: Message, session: AsyncSession, telegram_user_id: int
) -> None:
    """Ручная доставка на профиль админа: Delivery + GeneratedMessage,
    кнопки реакций, без сдвига next_run. Даты с 2099-01-01, чтобы не
    занять сегодняшний плановый слот."""
    if not is_admin_telegram_id(telegram_user_id):
        return

    user = await UserRepository(session).get_by_telegram_id(telegram_user_id)
    if user is None:
        await reply_target.answer("Профиль не найден — сначала пройдите /start.")
        return
    if user.status != UserStatus.ACTIVE:
        await reply_target.answer(
            f"Онбординг не завершён (status={user.status.value}) — генерация требует "
            "активного профиля."
        )
        return

    settings = get_settings()
    service = ManualDeliveryService(session, create_ai_provider(settings))

    await reply_target.answer("Генерирую сообщение...")
    try:
        delivery, message = await service.create_and_generate(user)
    except ManualDeliveryError as exc:
        await reply_target.answer(f"Ошибка генерации: {html.escape(str(exc))}")
        return

    if not message.text:
        await service.mark_failed(delivery, "empty_text")
        await reply_target.answer("Пустой текст генерации.")
        return

    try:
        await reply_target.answer(message.text, reply_markup=feedback_keyboard(message.id))
    except TelegramAPIError:
        await service.mark_failed(delivery, "telegram_send_error")
        await reply_target.answer("Не удалось отправить сообщение.")
        return
    await service.mark_sent(delivery, message)


@router.message(Command("generate"))
async def on_generate(message: Message, session: AsyncSession) -> None:
    if message.from_user is None:
        return
    await run_admin_generation(message, session, message.from_user.id)
