from enum import StrEnum


class UserStatus(StrEnum):
    ONBOARDING = "onboarding"
    ACTIVE = "active"
    PAUSED = "paused"
    BLOCKED = "blocked"


class UserRole(StrEnum):
    AUTHOR = "author"
    RECIPIENT = "recipient"


class AddressMode(StrEnum):
    INFORMAL = "informal"  # "ты"
    FORMAL = "formal"  # "вы"


class AuthorOnboardingStep(StrEnum):
    CONSENT = "consent"
    GENRE = "genre"
    RECIPIENT_USERNAME = "recipient_username"
    ADDRESS_MODE = "address_mode"
    QUALITIES = "qualities"
    TOPICS = "topics"
    SUPPORT_PREFERENCES = "support_preferences"
    BLOCKED_TOPICS = "blocked_topics"
    STYLE_EXAMPLES = "style_examples"
    PORTRAIT_NOTES = "portrait_notes"
    SUMMARY = "summary"
    DONE = "done"


class RecipientOnboardingStep(StrEnum):
    CONSENT = "consent"
    TIMEZONE = "timezone"
    SCHEDULE_MODE = "schedule_mode"
    SCHEDULE_TIME = "schedule_time"
    DONE = "done"
