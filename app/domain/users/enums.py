from enum import StrEnum


class UserStatus(StrEnum):
    ONBOARDING = "onboarding"
    ACTIVE = "active"
    PAUSED = "paused"
    BLOCKED = "blocked"


class AddressMode(StrEnum):
    INFORMAL = "informal"  # "ты"
    FORMAL = "formal"  # "вы"


class OnboardingStep(StrEnum):
    CONSENT = "consent"
    ADDRESS_MODE = "address_mode"
    QUALITIES = "qualities"
    TOPICS = "topics"
    SUPPORT_PREFERENCES = "support_preferences"
    BLOCKED_TOPICS = "blocked_topics"
    STYLE_EXAMPLES = "style_examples"
    TIMEZONE = "timezone"
    SCHEDULE_MODE = "schedule_mode"
    SCHEDULE_TIME = "schedule_time"
    SUMMARY = "summary"
    DONE = "done"
