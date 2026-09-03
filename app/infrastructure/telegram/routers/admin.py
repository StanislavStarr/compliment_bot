"""Служебные команды для проверки внутренней механики бота. Не часть
продуктового сценария — доступны только `ADMIN_TELEGRAM_ID` из настроек."""

from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.domain.users.enums import UserStatus
from app.infrastructure.db.repositories.users import UserRepository
from app.infrastructure.telegram.unscheduled import send_unscheduled_message

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

    await reply_target.answer("Генерирую сообщение...")
    sent = await send_unscheduled_message(reply_target, session, user)
    if not sent:
        await reply_target.answer("Не удалось сгенерировать сообщение. Попробуйте ещё раз.")


@router.message(Command("generate"))
async def on_generate(message: Message, session: AsyncSession) -> None:
    if message.from_user is None:
        return
    await run_admin_generation(message, session, message.from_user.id)
