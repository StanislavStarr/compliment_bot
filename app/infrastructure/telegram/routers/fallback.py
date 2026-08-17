"""Регистрируется последним в диспетчере — ловит апдейты, не подошедшие ни
одному хендлеру выше (например, если FSM-состояние потеряно после сбоя)."""

from aiogram import Router
from aiogram.types import CallbackQuery, Message

router = Router(name="fallback")


@router.message()
async def on_unhandled_message(message: Message) -> None:
    await message.answer("Не совсем понял. Отправьте /start, чтобы продолжить настройку.")


@router.callback_query()
async def on_unhandled_callback(callback: CallbackQuery) -> None:
    await callback.answer(
        "Эта кнопка уже неактуальна. Отправьте /start, чтобы продолжить.", show_alert=True
    )
