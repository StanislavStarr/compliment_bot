from aiogram.fsm.state import State, StatesGroup


class RecipientOnboarding(StatesGroup):
    consent = State()
    timezone_select = State()
    timezone_manual = State()
    schedule_mode = State()
    schedule_time_select = State()
    schedule_time_manual = State()
    schedule_period_select = State()
