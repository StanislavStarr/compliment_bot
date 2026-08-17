from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.storage.redis import RedisStorage

from app.config import Settings
from app.infrastructure.telegram.middlewares.db_session import DbSessionMiddleware
from app.infrastructure.telegram.routers.fallback import router as fallback_router
from app.infrastructure.telegram.routers.onboarding import router as onboarding_router
from app.infrastructure.telegram.routers.start import router as start_router


def create_bot(settings: Settings) -> Bot:
    return Bot(
        token=settings.telegram_bot_token.get_secret_value(),
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )


def create_dispatcher(settings: Settings) -> Dispatcher:
    storage = RedisStorage.from_url(settings.fsm_storage_url)
    dispatcher = Dispatcher(storage=storage)

    dispatcher.update.middleware(DbSessionMiddleware())

    dispatcher.include_router(start_router)
    dispatcher.include_router(onboarding_router)
    dispatcher.include_router(fallback_router)

    return dispatcher
