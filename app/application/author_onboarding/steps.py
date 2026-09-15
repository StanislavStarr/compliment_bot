from app.domain.messages.enums import MessageType
from app.domain.users.enums import AuthorOnboardingStep

AUTHOR_STEP_ORDER: list[AuthorOnboardingStep] = [
    AuthorOnboardingStep.CONSENT,
    AuthorOnboardingStep.GENRE,
    AuthorOnboardingStep.RECIPIENT_USERNAME,
    AuthorOnboardingStep.ADDRESS_MODE,
    AuthorOnboardingStep.QUALITIES,
    AuthorOnboardingStep.TOPICS,
    AuthorOnboardingStep.SUPPORT_PREFERENCES,
    AuthorOnboardingStep.BLOCKED_TOPICS,
    AuthorOnboardingStep.STYLE_EXAMPLES,
    AuthorOnboardingStep.PORTRAIT_NOTES,
    AuthorOnboardingStep.SUMMARY,
    AuthorOnboardingStep.DONE,
]


def next_author_step(
    current: AuthorOnboardingStep,
    message_type: MessageType | None = None,
) -> AuthorOnboardingStep:
    index = AUTHOR_STEP_ORDER.index(current)
    if index + 1 >= len(AUTHOR_STEP_ORDER):
        return AuthorOnboardingStep.DONE
    nxt = AUTHOR_STEP_ORDER[index + 1]
    if nxt is AuthorOnboardingStep.SUPPORT_PREFERENCES and message_type is MessageType.COMPLIMENT:
        return AuthorOnboardingStep.BLOCKED_TOPICS
    return nxt
