import random
import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime, time

from sqlalchemy.ext.asyncio import AsyncSession

from app.application.scheduling.calculator import (
    compute_next_run_for_exact_time,
    compute_next_run_for_period,
)
from app.domain.profiles.constants import SUPPORT_PREFERENCE_OPTIONS
from app.domain.schedules.enums import Period, ScheduleMode
from app.domain.users.enums import AddressMode, OnboardingStep, UserStatus
from app.infrastructure.db.models.profiles import Quality, StyleExample
from app.infrastructure.db.models.topics import Topic
from app.infrastructure.db.models.users import User
from app.infrastructure.db.repositories.blocked_topics import BlockedTopicRepository
from app.infrastructure.db.repositories.profiles import ProfileRepository
from app.infrastructure.db.repositories.qualities import QualityRepository, UserQualityRepository
from app.infrastructure.db.repositories.schedules import ScheduleRepository
from app.infrastructure.db.repositories.style_examples import StyleExampleRepository
from app.infrastructure.db.repositories.support_preferences import SupportPreferenceRepository
from app.infrastructure.db.repositories.topics import TopicRepository, UserTopicRepository
from app.infrastructure.db.repositories.users import UserRepository


@dataclass
class OnboardingSummary:
    address_mode: AddressMode | None
    qualities: list[str]
    topics: list[str]
    support_preferences: list[str]
    blocked_topics: list[str]
    style_examples_count: int
    timezone_name: str | None
    schedule_mode: ScheduleMode | None
    exact_local_time: time | None
    period: Period | None
    custom_texts: dict[str, str] = field(default_factory=dict)


class OnboardingService:
    """Тонкий фасад над репозиториями для сценария онбординга.

    Каждый шаг сохраняется сразу в БД (требование "без потери прогресса"),
    кроме связки часовой пояс -> режим -> время: она пишется в `schedules`
    одной операцией в `finalize_schedule`, т.к. таблица `schedules` не
    допускает промежуточное состояние без `mode`/`next_run_at_utc`."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self.users = UserRepository(session)
        self.profiles = ProfileRepository(session)
        self.topics = TopicRepository(session)
        self.user_topics = UserTopicRepository(session)
        self.qualities = QualityRepository(session)
        self.user_qualities = UserQualityRepository(session)
        self.support_preferences = SupportPreferenceRepository(session)
        self.blocked_topics = BlockedTopicRepository(session)
        self.style_examples = StyleExampleRepository(session)
        self.schedules = ScheduleRepository(session)

    async def get_or_create_user(self, telegram_user_id: int, telegram_chat_id: int) -> User:
        user = await self.users.get_by_telegram_id(telegram_user_id)
        if user is not None:
            user.last_seen_at = datetime.now(UTC)
            await self._session.flush()
            return user
        user = await self.users.create(telegram_user_id, telegram_chat_id)
        await self.profiles.get_or_create(user.id)
        await self._session.commit()
        return user

    async def set_step(self, user: User, step: OnboardingStep) -> None:
        user.onboarding_step = step
        await self._session.commit()

    async def confirm_consent(self, user: User) -> None:
        user.is_adult_confirmed = True
        user.privacy_accepted_at = datetime.now(UTC)
        await self._session.commit()

    async def save_address_mode(self, user: User, mode: AddressMode) -> None:
        user.address_mode = mode
        await self._session.commit()

    async def list_qualities(self) -> list[Quality]:
        return await self.qualities.list_all()

    async def save_qualities(
        self,
        user: User,
        quality_ids: list[uuid.UUID],
        custom_text: str | None,
        is_sensitive: bool,
    ) -> None:
        await self.user_qualities.replace_for_user(user.id, quality_ids, custom_text, is_sensitive)
        await self._session.commit()

    async def list_topics(self) -> list[Topic]:
        return await self.topics.list_all()

    async def save_topics(self, user: User, topic_ids: list[uuid.UUID]) -> None:
        await self.user_topics.replace_for_user(user.id, topic_ids)
        await self._session.commit()

    async def save_support_preferences(
        self,
        user: User,
        preference_codes: list[str],
        custom_text: str | None,
        is_sensitive: bool,
    ) -> None:
        await self.support_preferences.replace_for_user(
            user.id, preference_codes, custom_text, is_sensitive
        )
        await self._session.commit()

    async def save_blocked_topics(
        self,
        user: User,
        topic_codes: list[str],
        custom_text: str | None,
        is_sensitive: bool,
    ) -> None:
        await self.blocked_topics.replace_for_user(user.id, topic_codes, custom_text, is_sensitive)
        await self._session.commit()

    async def add_style_example(self, user: User, text: str) -> StyleExample:
        example = await self.style_examples.add(user.id, text)
        await self._session.commit()
        return example

    async def finalize_schedule(
        self,
        user: User,
        timezone_name: str,
        mode: ScheduleMode,
        exact_local_time: time | None = None,
        period: Period | None = None,
    ) -> None:
        now_utc = datetime.now(UTC)
        if mode is ScheduleMode.EXACT:
            if exact_local_time is None:
                raise ValueError("exact_local_time обязателен для режима EXACT")
            next_run_at_utc = compute_next_run_for_exact_time(
                now_utc, timezone_name, exact_local_time
            )
        else:
            if period is None:
                raise ValueError("period обязателен для режима PERIOD")
            next_run_at_utc = compute_next_run_for_period(
                now_utc, timezone_name, period, random.Random()
            )

        await self.schedules.upsert(
            user_id=user.id,
            mode=mode,
            timezone_name=timezone_name,
            next_run_at_utc=next_run_at_utc,
            exact_local_time=exact_local_time,
            period=period,
        )
        await self._session.commit()

    async def complete_onboarding(self, user: User) -> None:
        user.status = UserStatus.ACTIVE
        user.onboarding_step = OnboardingStep.DONE
        await self._session.commit()

    async def build_summary(self, user: User) -> OnboardingSummary:
        all_topics = await self.topics.list_all()
        topics_by_id = {t.id: t.label for t in all_topics}
        topics_by_code = {t.code: t.label for t in all_topics}
        support_labels_by_code = dict(SUPPORT_PREFERENCE_OPTIONS)

        user_qualities = await self.user_qualities.list_for_user(user.id)
        user_topics = await self.user_topics.list_active_for_user(user.id)
        user_support = await self.support_preferences.list_for_user(user.id)
        user_blocked = await self.blocked_topics.list_for_user(user.id)
        schedule = await self.schedules.get_by_user_id(user.id)

        custom_texts: dict[str, str] = {}

        qualities_catalog = {q.id: q.label for q in await self.qualities.list_all()}
        quality_labels = []
        for uq in user_qualities:
            if uq.quality_id is not None:
                quality_labels.append(qualities_catalog.get(uq.quality_id, "?"))
            elif uq.custom_text:
                custom_texts["qualities"] = uq.custom_text

        topic_labels = [topics_by_id.get(ut.topic_id, "?") for ut in user_topics]

        support_labels = []
        for sp in user_support:
            if sp.preference_code is not None:
                support_labels.append(support_labels_by_code.get(sp.preference_code, "?"))
            elif sp.custom_text:
                custom_texts["support_preferences"] = sp.custom_text

        blocked_labels = []
        for bt in user_blocked:
            if bt.topic_code is not None:
                blocked_labels.append(topics_by_code.get(bt.topic_code, bt.topic_code))
            elif bt.custom_text:
                custom_texts["blocked_topics"] = bt.custom_text

        return OnboardingSummary(
            address_mode=user.address_mode,
            qualities=quality_labels,
            topics=topic_labels,
            support_preferences=support_labels,
            blocked_topics=blocked_labels,
            style_examples_count=len(await self.style_examples.list_active_for_user(user.id)),
            timezone_name=schedule.timezone_name if schedule else None,
            schedule_mode=schedule.mode if schedule else None,
            exact_local_time=schedule.exact_local_time if schedule else None,
            period=schedule.period if schedule else None,
            custom_texts=custom_texts,
        )
