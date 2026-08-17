from collections.abc import Awaitable, Callable
from typing import Any

from aiogram import BaseMiddleware
from aiogram.types import TelegramObject

from app.infrastructure.db.session import get_session_factory


class DbSessionMiddleware(BaseMiddleware):
    """Открывает одну AsyncSession на апдейт и кладёт её в data["session"].
    Хендлеры сами решают, когда коммитить (через OnboardingService)."""

    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        async with get_session_factory()() as session:
            data["session"] = session
            return await handler(event, data)
