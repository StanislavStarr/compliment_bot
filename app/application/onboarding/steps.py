from app.domain.users.enums import OnboardingStep

STEP_ORDER: list[OnboardingStep] = [
    OnboardingStep.CONSENT,
    OnboardingStep.ADDRESS_MODE,
    OnboardingStep.QUALITIES,
    OnboardingStep.TOPICS,
    OnboardingStep.SUPPORT_PREFERENCES,
    OnboardingStep.BLOCKED_TOPICS,
    OnboardingStep.STYLE_EXAMPLES,
    OnboardingStep.TIMEZONE,
    OnboardingStep.SCHEDULE_MODE,
    OnboardingStep.SCHEDULE_TIME,
    OnboardingStep.SUMMARY,
    OnboardingStep.DONE,
]


def next_step(current: OnboardingStep) -> OnboardingStep:
    """Следующий шаг онбординга по порядку. Для DONE возвращает DONE —
    вызывающий код не должен звать next_step после завершения онбординга."""
    index = STEP_ORDER.index(current)
    if index + 1 >= len(STEP_ORDER):
        return OnboardingStep.DONE
    return STEP_ORDER[index + 1]
