from aiogram.fsm.state import State, StatesGroup


class AuthorOnboarding(StatesGroup):
    consent = State()
    genre = State()
    recipient_username = State()
    address_mode = State()
    qualities_select = State()
    qualities_custom = State()
    topics_select = State()
    support_select = State()
    support_custom = State()
    blocked_select = State()
    blocked_custom = State()
    style_examples = State()
    portrait_notes = State()
    summary = State()
    edit_menu = State()
