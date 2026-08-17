from aiogram.fsm.state import State, StatesGroup


class Onboarding(StatesGroup):
    """Состояния FSM онбординга. Крупные шаги совпадают с `OnboardingStep`
    (персистится в `users.onboarding_step` для восстановления после /start),
    доп. под-состояния (`*_custom`, `*_manual`) — временные, только в рамках
    текущей сессии диалога."""

    consent = State()

    address_mode = State()

    qualities_select = State()
    qualities_custom = State()

    topics_select = State()

    support_select = State()
    support_custom = State()

    blocked_select = State()
    blocked_custom = State()

    style_examples = State()

    timezone_select = State()
    timezone_manual = State()

    schedule_mode = State()
    schedule_time_select = State()
    schedule_time_manual = State()
    schedule_period_select = State()

    summary = State()
    edit_menu = State()
