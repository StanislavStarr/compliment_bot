from app.domain.users.enums import RecipientOnboardingStep

RECIPIENT_STEP_ORDER: list[RecipientOnboardingStep] = [
    RecipientOnboardingStep.CONSENT,
    RecipientOnboardingStep.TIMEZONE,
    RecipientOnboardingStep.SCHEDULE_MODE,
    RecipientOnboardingStep.SCHEDULE_TIME,
    RecipientOnboardingStep.DONE,
]


def next_recipient_step(current: RecipientOnboardingStep) -> RecipientOnboardingStep:
    index = RECIPIENT_STEP_ORDER.index(current)
    if index + 1 >= len(RECIPIENT_STEP_ORDER):
        return RecipientOnboardingStep.DONE
    return RECIPIENT_STEP_ORDER[index + 1]
