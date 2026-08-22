import asyncio

from aiogram.types import BotCommand

from app.config import get_settings
from app.infrastructure.logging.setup import configure_logging, get_logger
from app.infrastructure.telegram.bot import create_bot, create_dispatcher

logger = get_logger(__name__)


async def main() -> None:
    settings = get_settings()
    configure_logging(settings.log_level)

    bot = create_bot(settings)
    dispatcher = create_dispatcher(settings)

    logger.info("bot_starting", environment=settings.environment)
    await bot.delete_webhook(drop_pending_updates=True)
    await bot.set_my_commands(
        [
            BotCommand(command="start", description="Начать или открыть настройки"),
            BotCommand(command="settings", description="Профиль и расписание"),
            BotCommand(command="pause", description="Приостановить сообщения"),
            BotCommand(command="resume", description="Возобновить сообщения"),
            BotCommand(command="help", description="Как работает бот"),
        ]
    )
    await dispatcher.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
