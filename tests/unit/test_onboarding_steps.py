from app.application.author_onboarding.steps import AUTHOR_STEP_ORDER, next_author_step
from app.application.recipient_onboarding.steps import RECIPIENT_STEP_ORDER, next_recipient_step
from app.domain.messages.enums import MessageType
from app.domain.users.enums import AuthorOnboardingStep, RecipientOnboardingStep


def test_author_step_order_covers_all() -> None:
    assert set(AUTHOR_STEP_ORDER) == set(AuthorOnboardingStep)


def test_author_next_step_follows_declared_order() -> None:
    for current, expected in zip(AUTHOR_STEP_ORDER, AUTHOR_STEP_ORDER[1:], strict=False):
        assert next_author_step(current) == expected


def test_author_next_step_after_done_stays_done() -> None:
    assert next_author_step(AuthorOnboardingStep.DONE) == AuthorOnboardingStep.DONE


def test_author_compliment_skips_support_preferences() -> None:
    assert (
        next_author_step(AuthorOnboardingStep.TOPICS, MessageType.COMPLIMENT)
        == AuthorOnboardingStep.BLOCKED_TOPICS
    )
    assert (
        next_author_step(AuthorOnboardingStep.TOPICS, MessageType.SUPPORT)
        == AuthorOnboardingStep.SUPPORT_PREFERENCES
    )


def test_recipient_step_order_covers_all() -> None:
    assert set(RECIPIENT_STEP_ORDER) == set(RecipientOnboardingStep)


def test_recipient_next_step_follows_declared_order() -> None:
    for current, expected in zip(RECIPIENT_STEP_ORDER, RECIPIENT_STEP_ORDER[1:], strict=False):
        assert next_recipient_step(current) == expected


def test_recipient_next_step_after_done_stays_done() -> None:
    assert next_recipient_step(RecipientOnboardingStep.DONE) == RecipientOnboardingStep.DONE
