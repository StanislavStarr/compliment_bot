from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, InlineKeyboardMarkup, Message

Event = Message | CallbackQuery


def cb_data(callback: CallbackQuery) -> str:
    assert callback.data is not None
    return callback.data


def cb_message(callback: CallbackQuery) -> Message:
    assert isinstance(callback.message, Message)
    return callback.message


def message_text(message: Message) -> str:
    assert message.text is not None
    return message.text


def telegram_user_id(event: Event) -> int:
    assert event.from_user is not None
    return event.from_user.id


async def send(event: Event, text: str, keyboard: InlineKeyboardMarkup | None = None) -> None:
    target = cb_message(event) if isinstance(event, CallbackQuery) else event
    await target.answer(text, reply_markup=keyboard)


async def bot_username(event: Event) -> str:
    bot = event.bot
    assert bot is not None
    me = await bot.get_me()
    assert me.username is not None
    return me.username


async def clear_markup(callback: CallbackQuery) -> None:
    await cb_message(callback).edit_reply_markup(reply_markup=None)


async def mark_edit_mode(state: FSMContext) -> None:
    await state.update_data(edit_mode=True)
