from aiogram.fsm.context import FSMContext

from app.application.author_onboarding.service import AuthorOnboardingService
from app.domain.messages.enums import MessageType
from app.domain.users.enums import AuthorOnboardingStep
from app.infrastructure.db.models.users import User
from app.infrastructure.telegram.helpers import Event
from app.infrastructure.telegram.routers.author.consent import render_consent
from app.infrastructure.telegram.routers.author.genre import render_genre
from app.infrastructure.telegram.routers.author.portrait import (
    render_address_mode,
    render_blocked,
    render_portrait_notes,
    render_qualities,
    render_style_examples,
    render_support,
    render_topics,
)
from app.infrastructure.telegram.routers.author.recipient import render_recipient_username
from app.infrastructure.telegram.routers.author.summary import render_author_home, render_summary


async def render_author_step(
    event: Event,
    state: FSMContext,
    service: AuthorOnboardingService,
    user: User,
    step: AuthorOnboardingStep | None = None,
) -> None:
    current = step or user.author_step or AuthorOnboardingStep.CONSENT
    if current is AuthorOnboardingStep.SUPPORT_PREFERENCES:
        order = await service.draft_order(user)
        if order.message_type is MessageType.COMPLIMENT:
            current = AuthorOnboardingStep.BLOCKED_TOPICS
            await service.set_step(user, current)

    if current is AuthorOnboardingStep.CONSENT:
        await render_consent(event, state)
    elif current is AuthorOnboardingStep.GENRE:
        await render_genre(event, state)
    elif current is AuthorOnboardingStep.RECIPIENT_USERNAME:
        await render_recipient_username(event, state)
    elif current is AuthorOnboardingStep.ADDRESS_MODE:
        await render_address_mode(event, state)
    elif current is AuthorOnboardingStep.QUALITIES:
        await render_qualities(event, state, service)
    elif current is AuthorOnboardingStep.TOPICS:
        await render_topics(event, state, service)
    elif current is AuthorOnboardingStep.SUPPORT_PREFERENCES:
        await render_support(event, state)
    elif current is AuthorOnboardingStep.BLOCKED_TOPICS:
        await render_blocked(event, state, service)
    elif current is AuthorOnboardingStep.STYLE_EXAMPLES:
        await render_style_examples(event, state)
    elif current is AuthorOnboardingStep.PORTRAIT_NOTES:
        await render_portrait_notes(event, state)
    elif current is AuthorOnboardingStep.SUMMARY:
        await render_summary(event, state, service, user)
    elif current is AuthorOnboardingStep.DONE:
        await render_author_home(event, state, service._session, user)
    else:
        await render_consent(event, state)
