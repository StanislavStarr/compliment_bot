import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.application.author_onboarding.steps import next_author_step
from app.application.invites.service import InviteService, IssuedInvite
from app.application.orders.service import OrderService
from app.domain.messages.enums import MessageType
from app.domain.profiles.constants import SUPPORT_PREFERENCE_OPTIONS
from app.domain.users.enums import AddressMode, AuthorOnboardingStep, UserRole
from app.domain.users.usernames import normalize_telegram_username
from app.infrastructure.db.models.orders import Order
from app.infrastructure.db.models.profiles import Quality, StyleExample
from app.infrastructure.db.models.topics import Topic
from app.infrastructure.db.models.users import User
from app.infrastructure.db.repositories.blocked_topics import BlockedTopicRepository
from app.infrastructure.db.repositories.profiles import ProfileRepository
from app.infrastructure.db.repositories.qualities import OrderQualityRepository, QualityRepository
from app.infrastructure.db.repositories.style_examples import StyleExampleRepository
from app.infrastructure.db.repositories.support_preferences import SupportPreferenceRepository
from app.infrastructure.db.repositories.topics import OrderTopicRepository, TopicRepository
from app.infrastructure.db.repositories.users import UserRepository


class AuthorOnboardingError(Exception):
    pass


@dataclass
class AuthorOnboardingSummary:
    message_type: MessageType | None
    recipient_username: str | None
    address_mode: AddressMode | None
    qualities: list[str]
    topics: list[str]
    support_preferences: list[str]
    blocked_topics: list[str]
    style_examples_count: int
    portrait_notes: str | None
    custom_texts: dict[str, str] = field(default_factory=dict)


class AuthorOnboardingService:
    """Онбординг дарителя: портрет и жанр в заказ. Расписание сюда не входит."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self.users = UserRepository(session)
        self.profiles = ProfileRepository(session)
        self.orders = OrderService(session)
        self.invites = InviteService(session)
        self.topics = TopicRepository(session)
        self.order_topics = OrderTopicRepository(session)
        self.qualities = QualityRepository(session)
        self.order_qualities = OrderQualityRepository(session)
        self.support_preferences = SupportPreferenceRepository(session)
        self.blocked_topics = BlockedTopicRepository(session)
        self.style_examples = StyleExampleRepository(session)

    async def get_or_create_user(
        self,
        telegram_user_id: int,
        telegram_chat_id: int,
        telegram_username: str | None = None,
    ) -> User:
        username = normalize_telegram_username(telegram_username)
        user = await self.users.get_by_telegram_id(telegram_user_id)
        if user is not None:
            user.last_seen_at = datetime.now(UTC)
            user.telegram_username = username
            if user.role is None:
                user.role = UserRole.AUTHOR
            await self._session.commit()
            return user
        user = await self.users.create(
            telegram_user_id,
            telegram_chat_id,
            telegram_username=username,
            role=UserRole.AUTHOR,
            author_step=AuthorOnboardingStep.CONSENT,
        )
        await self.profiles.get_or_create(user.id)
        await self._session.commit()
        return user

    async def draft_order(self, author: User) -> Order:
        return await self.orders.get_or_create_draft(author)

    async def set_step(self, author: User, step: AuthorOnboardingStep) -> None:
        author.author_step = step
        await self._session.commit()

    async def advance_step(self, author: User, order: Order) -> AuthorOnboardingStep:
        current = author.author_step or AuthorOnboardingStep.CONSENT
        nxt = next_author_step(current, order.message_type)
        await self.set_step(author, nxt)
        return nxt

    async def confirm_consent(self, author: User) -> None:
        author.is_adult_confirmed = True
        author.privacy_accepted_at = datetime.now(UTC)
        await self._session.commit()

    async def save_genre(self, author: User, message_type: MessageType) -> Order:
        order = await self.draft_order(author)
        order.message_type = message_type
        await self._session.commit()
        return order

    async def save_recipient_username(self, author: User, raw_username: str) -> Order:
        username = normalize_telegram_username(raw_username)
        if username is None:
            raise AuthorOnboardingError("укажите username адресата")
        order = await self.draft_order(author)
        order.recipient_username = username
        await self._session.commit()
        return order

    async def save_address_mode(self, author: User, mode: AddressMode) -> Order:
        order = await self.draft_order(author)
        order.address_mode = mode
        await self._session.commit()
        return order

    async def list_qualities(self) -> list[Quality]:
        return await self.qualities.list_all()

    async def save_qualities(
        self,
        author: User,
        quality_ids: list[uuid.UUID],
        custom_text: str | None,
        is_sensitive: bool,
    ) -> None:
        order = await self.draft_order(author)
        await self.order_qualities.replace_for_order(
            order.id, quality_ids, custom_text, is_sensitive
        )
        if is_sensitive:
            order.sensitive_input_present = True
        await self._session.commit()

    async def list_topics(self) -> list[Topic]:
        return await self.topics.list_all()

    async def save_topics(self, author: User, topic_ids: list[uuid.UUID]) -> None:
        order = await self.draft_order(author)
        await self.order_topics.replace_for_order(order.id, topic_ids)
        await self._session.commit()

    async def save_support_preferences(
        self,
        author: User,
        preference_codes: list[str],
        custom_text: str | None,
        is_sensitive: bool,
    ) -> None:
        order = await self.draft_order(author)
        await self.support_preferences.replace_for_order(
            order.id, preference_codes, custom_text, is_sensitive
        )
        if is_sensitive:
            order.sensitive_input_present = True
        await self._session.commit()

    async def save_blocked_topics(
        self,
        author: User,
        topic_codes: list[str],
        custom_text: str | None,
        is_sensitive: bool,
    ) -> None:
        order = await self.draft_order(author)
        await self.blocked_topics.replace_for_order(
            order.id, topic_codes, custom_text, is_sensitive
        )
        if is_sensitive:
            order.sensitive_input_present = True
        await self._session.commit()

    async def add_style_example(self, author: User, text: str) -> StyleExample:
        order = await self.draft_order(author)
        example = await self.style_examples.add(order.id, text)
        await self._session.commit()
        return example

    async def save_portrait_notes(self, author: User, notes: str | None) -> Order:
        order = await self.draft_order(author)
        text = notes.strip() if notes else None
        order.portrait_notes = text or None
        await self._session.commit()
        return order

    async def complete(self, author: User) -> None:
        author.author_step = AuthorOnboardingStep.DONE
        await self._session.commit()

    async def issue_invite(self, author: User, bot_username: str) -> IssuedInvite:
        if normalize_telegram_username(author.telegram_username) is None:
            raise AuthorOnboardingError("у автора должен быть username в Telegram")
        order = await self.draft_order(author)
        issued = await self.invites.issue(order, bot_username)
        await self.complete(author)
        return issued

    async def build_summary(self, author: User) -> AuthorOnboardingSummary:
        order = await self.draft_order(author)
        all_topics = await self.topics.list_all()
        topics_by_id = {t.id: t.label for t in all_topics}
        topics_by_code = {t.code: t.label for t in all_topics}
        support_labels_by_code = dict(SUPPORT_PREFERENCE_OPTIONS)

        order_qualities = await self.order_qualities.list_for_order(order.id)
        order_topics = await self.order_topics.list_active_for_order(order.id)
        order_support = await self.support_preferences.list_for_order(order.id)
        order_blocked = await self.blocked_topics.list_for_order(order.id)

        custom_texts: dict[str, str] = {}
        qualities_catalog = {q.id: q.label for q in await self.qualities.list_all()}
        quality_labels = []
        for uq in order_qualities:
            if uq.quality_id is not None:
                quality_labels.append(qualities_catalog.get(uq.quality_id, "?"))
            elif uq.custom_text:
                custom_texts["qualities"] = uq.custom_text

        topic_labels = [topics_by_id.get(ut.topic_id, "?") for ut in order_topics]
        support_labels = []
        for sp in order_support:
            if sp.preference_code is not None:
                support_labels.append(support_labels_by_code.get(sp.preference_code, "?"))
            elif sp.custom_text:
                custom_texts["support_preferences"] = sp.custom_text

        blocked_labels = []
        for bt in order_blocked:
            if bt.topic_code is not None:
                blocked_labels.append(topics_by_code.get(bt.topic_code, bt.topic_code))
            elif bt.custom_text:
                custom_texts["blocked_topics"] = bt.custom_text

        return AuthorOnboardingSummary(
            message_type=order.message_type,
            recipient_username=order.recipient_username,
            address_mode=order.address_mode,
            qualities=quality_labels,
            topics=topic_labels,
            support_preferences=support_labels,
            blocked_topics=blocked_labels,
            style_examples_count=len(await self.style_examples.list_active_for_order(order.id)),
            portrait_notes=order.portrait_notes,
            custom_texts=custom_texts,
        )
