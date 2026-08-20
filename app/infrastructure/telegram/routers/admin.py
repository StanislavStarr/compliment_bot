"""Служебные команды для проверки внутренней механики бота. Не часть
продуктового сценария — доступны только `ADMIN_TELEGRAM_ID` из настроек."""

import html

from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message
from sqlalchemy.ext.asyncio import AsyncSession

from app.application.generation.service import GenerationError, GenerationService
from app.config import get_settings
from app.domain.users.enums import UserStatus
from app.infrastructure.ai.factory import create_ai_provider
from app.infrastructure.db.repositories.users import UserRepository

router = Router(name="admin")


def _is_admin(message: Message) -> bool:
    settings = get_settings()
    return (
        settings.admin_telegram_id is not None
        and message.from_user is not None
        and message.from_user.id == settings.admin_telegram_id
    )


@router.message(Command("generate"))
async def on_generate(message: Message, session: AsyncSession) -> None:
    """Тестовая генерация одного сообщения для собственного профиля админа —
    без создания `Delivery`/`GeneratedMessage` в БД, просто показывает
    результат pipeline (текст + метаданные) в чате. Реальная доставка
    остаётся за `tasks.deliver_message` (Этап 5)."""
    if not _is_admin(message):
        return

    assert message.from_user is not None
    user = await UserRepository(session).get_by_telegram_id(message.from_user.id)
    if user is None:
        await message.answer("Профиль не найден — сначала пройдите /start.")
        return
    if user.status != UserStatus.ACTIVE:
        await message.answer(
            f"Онбординг не завершён (status={user.status.value}) — генерация требует "
            "активного профиля."
        )
        return

    settings = get_settings()
    provider = create_ai_provider(settings)
    service = GenerationService(session, provider)

    await message.answer("Генерирую тестовое сообщение...")
    try:
        outcome = await service.generate(user)
    except GenerationError as exc:
        await message.answer(f"Ошибка генерации: {html.escape(str(exc))}")
        return

    tokens = f"{outcome.input_tokens}/{outcome.output_tokens}/{outcome.total_tokens}"
    reply = (
        f"<b>Источник:</b> {outcome.source.value}\n"
        f"<b>Тип:</b> {outcome.message_type.value}\n"
        f"<b>Тема:</b> {html.escape(outcome.theme)}\n"
        f"<b>Semantic key:</b> {html.escape(outcome.semantic_key)}\n"
        f"<b>Provider/model:</b> {outcome.provider or '—'} / {outcome.model or '—'}\n"
        f"<b>Токены (in/out/total):</b> {tokens}\n"
        f"<b>Validation:</b> {outcome.validation_status}\n"
        f"<b>Prompt version:</b> {outcome.prompt_version or '—'}\n\n"
        f"{html.escape(outcome.text)}"
    )
    await message.answer(reply)
