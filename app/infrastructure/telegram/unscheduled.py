from aiogram.exceptions import TelegramAPIError
from aiogram.types import Message
from sqlalchemy.ext.asyncio import AsyncSession

from app.application.admin.service import ManualDeliveryError, ManualDeliveryService
from app.config import get_settings
from app.infrastructure.ai.factory import create_ai_provider
from app.infrastructure.db.models.users import User
from app.infrastructure.logging.setup import get_logger
from app.infrastructure.telegram.keyboards.feedback import feedback_keyboard

logger = get_logger(__name__)


async def send_unscheduled_message(
    reply_target: Message, session: AsyncSession, user: User
) -> bool:
    """Внеплановая доставка: пишет Delivery/GeneratedMessage на дату с 2099,
    шлёт текст с кнопками реакций, next_run не трогает."""
    settings = get_settings()
    service = ManualDeliveryService(session, create_ai_provider(settings))
    try:
        delivery, message = await service.create_and_generate(user)
    except ManualDeliveryError as exc:
        logger.warning("unscheduled_delivery_failed", user_id=str(user.id), error=str(exc))
        return False

    if not message.text:
        await service.mark_failed(delivery, "empty_text")
        return False

    try:
        await reply_target.answer(message.text, reply_markup=feedback_keyboard(message.id))
    except TelegramAPIError as exc:
        await service.mark_failed(delivery, "telegram_send_error")
        logger.warning("unscheduled_send_failed", user_id=str(user.id), error=str(exc))
        return False

    await service.mark_sent(delivery, message)
    return True
