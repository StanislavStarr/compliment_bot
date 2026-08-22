import uuid

from aiogram import F, Router
from aiogram.types import CallbackQuery, Message
from sqlalchemy.ext.asyncio import AsyncSession

from app.application.feedback.service import (
    FeedbackAlreadyExistsError,
    FeedbackNotFoundError,
    FeedbackService,
)
from app.application.onboarding.service import OnboardingService
from app.domain.feedback.enums import ReactionType
from app.infrastructure.db.models.users import User
from app.infrastructure.telegram.keyboards.feedback import dislike_reasons_keyboard

router = Router(name="feedback")

_THANKS = {
    ReactionType.LIKED: "Спасибо, учту этот тон в следующих сообщениях.",
    ReactionType.REPEATED: "Понял, такую формулировку повторять не буду.",
    ReactionType.DISLIKED: "Спасибо, учту при следующих сообщениях.",
}


def _message_id(token: str) -> uuid.UUID:
    return uuid.UUID(hex=token)


async def _user_or_none(callback: CallbackQuery, session: AsyncSession) -> User | None:
    assert callback.from_user is not None
    return await OnboardingService(session).users.get_by_telegram_id(callback.from_user.id)


def _cb_message(callback: CallbackQuery) -> Message | None:
    return callback.message if isinstance(callback.message, Message) else None


@router.callback_query(F.data.startswith("fb:l:"))
async def on_like(callback: CallbackQuery, session: AsyncSession) -> None:
    await _submit(callback, session, ReactionType.LIKED)


@router.callback_query(F.data.startswith("fb:p:"))
async def on_repeated(callback: CallbackQuery, session: AsyncSession) -> None:
    await _submit(callback, session, ReactionType.REPEATED)


@router.callback_query(F.data.startswith("fb:d:"))
async def on_dislike(callback: CallbackQuery) -> None:
    token = callback.data.split(":", 2)[2] if callback.data else ""
    await callback.answer()
    msg = _cb_message(callback)
    if msg is not None:
        await msg.edit_reply_markup(reply_markup=dislike_reasons_keyboard(_message_id(token)))


@router.callback_query(F.data.startswith("fb:r:"))
async def on_dislike_reason(callback: CallbackQuery, session: AsyncSession) -> None:
    assert callback.data is not None
    _, _, token, reason = callback.data.split(":", 3)
    await _submit(callback, session, ReactionType.DISLIKED, reason_code=reason)


@router.callback_query(F.data.startswith("fb:s:"))
async def on_dislike_skip(callback: CallbackQuery, session: AsyncSession) -> None:
    await _submit(callback, session, ReactionType.DISLIKED)


async def _submit(
    callback: CallbackQuery,
    session: AsyncSession,
    reaction: ReactionType,
    reason_code: str | None = None,
) -> None:
    user = await _user_or_none(callback, session)
    if user is None or callback.data is None:
        await callback.answer("Не удалось сохранить реакцию.", show_alert=True)
        return

    parts = callback.data.split(":")
    token = parts[2]
    service = FeedbackService(session)
    try:
        await service.submit(user, _message_id(token), reaction, reason_code=reason_code)
    except FeedbackAlreadyExistsError:
        await callback.answer("Реакция уже сохранена.", show_alert=True)
        msg = _cb_message(callback)
        if msg is not None:
            await msg.edit_reply_markup(reply_markup=None)
        return
    except FeedbackNotFoundError:
        await callback.answer("Это сообщение уже недоступно.", show_alert=True)
        return

    await callback.answer()
    msg = _cb_message(callback)
    if msg is not None:
        await msg.edit_reply_markup(reply_markup=None)
        await msg.answer(_THANKS[reaction])
