from app.application.onboarding.steps import STEP_ORDER, next_step
from app.domain.users.enums import OnboardingStep


def test_step_order_covers_all_enum_values() -> None:
    assert set(STEP_ORDER) == set(OnboardingStep)


def test_next_step_follows_declared_order() -> None:
    for current, expected in zip(STEP_ORDER, STEP_ORDER[1:], strict=False):
        assert next_step(current) == expected


def test_next_step_after_done_stays_done() -> None:
    assert next_step(OnboardingStep.DONE) == OnboardingStep.DONE
