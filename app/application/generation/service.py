import random
from dataclasses import dataclass

from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.messages.constants import (
    CURRENT_PROMPT_VERSION,
    MAX_LIKED_EXAMPLES_IN_PROMPT,
    MAX_RECENT_MESSAGES_IN_PROMPT,
    MAX_REFERENCE_EXAMPLES_IN_PROMPT,
)
from app.domain.messages.enums import MessageSource, MessageType
from app.domain.profiles.constants import SUPPORT_PREFERENCE_OPTIONS
from app.domain.users.enums import AddressMode
from app.infrastructure.ai.base import (
    AIGenerationResult,
    AIProvider,
    AIProviderError,
    GenerationRequest,
    RecentMessageContext,
    ReferenceExample,
)
from app.infrastructure.ai.validators.duplicate_checker import find_duplicate_reason
from app.infrastructure.ai.validators.message_validator import validate_message
from app.infrastructure.db.models.users import User
from app.infrastructure.db.repositories.blocked_topics import BlockedTopicRepository
from app.infrastructure.db.repositories.fallback_messages import FallbackMessageRepository
from app.infrastructure.db.repositories.feedback import FeedbackRepository
from app.infrastructure.db.repositories.messages import GeneratedMessageRepository
from app.infrastructure.db.repositories.qualities import QualityRepository, UserQualityRepository
from app.infrastructure.db.repositories.style_examples import StyleExampleRepository
from app.infrastructure.db.repositories.support_preferences import SupportPreferenceRepository
from app.infrastructure.db.repositories.topics import TopicRepository, UserTopicRepository


class GenerationError(Exception):
    """Данных пользователя недостаточно для генерации (например, нет
    активных тем или нет резервных сообщений для темы/типа) — сигнал о баге
    в данных/сидировании, а не штатный fallback-сценарий."""


@dataclass
class GenerationOutcome:
    text: str
    message_type: MessageType
    theme: str
    semantic_key: str
    source: MessageSource
    provider: str | None
    model: str | None
    input_tokens: int | None
    output_tokens: int | None
    total_tokens: int | None
    prompt_version: str | None
    validation_status: str


class GenerationService:
    """Оркестрация pipeline: выбор темы/типа, сбор
    обезличенного контекста, вызов провайдера, локальная валидация, защита
    от повторов, один повтор при нарушении, fallback при исчерпании попыток.

    Персист в `generated_messages`/`deliveries` сюда не входит — это часть
    delivery-таска Этапа 5, у которого уже есть готовый `delivery_id`."""

    def __init__(self, session: AsyncSession, provider: AIProvider) -> None:
        self._provider = provider
        self.topics = TopicRepository(session)
        self.user_topics = UserTopicRepository(session)
        self.qualities = QualityRepository(session)
        self.user_qualities = UserQualityRepository(session)
        self.support_preferences = SupportPreferenceRepository(session)
        self.blocked_topics = BlockedTopicRepository(session)
        self.style_examples = StyleExampleRepository(session)
        self.generated_messages = GeneratedMessageRepository(session)
        self.feedback = FeedbackRepository(session)
        self.fallback_messages = FallbackMessageRepository(session)

    async def generate(
        self, user: User, message_type: MessageType | None = None
    ) -> GenerationOutcome:
        """Удобный вариант "всегда успешен" — сам решает AI vs fallback.
        Использовать вне delivery-таска (ручная проверка, будущие admin-сценарии).
        Delivery-таск (Этап 5) вызывает `generate_via_ai_or_raise` и
        `generate_fallback_only` по отдельности, чтобы техническая ошибка
        провайдера могла ретраиться на уровне Celery, а не тонуть здесь.
        `message_type` задаёт жанр вручную; `None` — чередование как в доставке."""
        try:
            return await self.generate_via_ai_or_raise(user, message_type=message_type)
        except AIProviderError:
            return await self.generate_fallback_only(user, message_type=message_type)

    async def generate_via_ai_or_raise(
        self, user: User, message_type: MessageType | None = None
    ) -> GenerationOutcome:
        """Технические ошибки провайдера (`AIProviderError`) пробрасываются
        наверх — вызывающий код (delivery-таск) решает, ретраить ли через
        Celery. Невалидный/повторяющийся ответ после одного повтора — это
        не техническая ошибка, поэтому здесь тихо уходит в fallback."""
        request, recent_messages = await self._build_request(user, message_type=message_type)

        result = await self._provider.generate_message(request)
        problems = self._check(result, request, recent_messages)

        if problems:
            request.retry_reason = "; ".join(problems)
            result = await self._provider.generate_message(request)
            problems = self._check(result, request, recent_messages)
            if problems:
                return await self._pick_fallback(request, recent_messages)

        return GenerationOutcome(
            text=result.text,
            message_type=result.message_type,
            theme=result.theme,
            semantic_key=result.semantic_key,
            source=MessageSource.AI,
            provider="openai",
            model=result.model,
            input_tokens=result.input_tokens,
            output_tokens=result.output_tokens,
            total_tokens=result.total_tokens,
            prompt_version=CURRENT_PROMPT_VERSION,
            validation_status="ok",
        )

    async def generate_fallback_only(
        self, user: User, message_type: MessageType | None = None
    ) -> GenerationOutcome:
        """Используется после исчерпания Celery retries по AIProviderError —
        к провайдеру больше не обращаемся, сразу берём резервную фразу."""
        request, recent_messages = await self._build_request(user, message_type=message_type)
        return await self._pick_fallback(request, recent_messages)

    def _check(
        self,
        result: AIGenerationResult,
        request: GenerationRequest,
        recent_messages: list[RecentMessageContext],
    ) -> list[str]:
        problems = validate_message(result, request)
        duplicate_reason = find_duplicate_reason(result, recent_messages)
        if duplicate_reason:
            problems.append(duplicate_reason)
        return problems

    async def _build_request(
        self, user: User, message_type: MessageType | None = None
    ) -> tuple[GenerationRequest, list[RecentMessageContext]]:
        topic_code, topic_label, selected_type = await self._select_topic_and_type(user)
        if message_type is not None:
            selected_type = message_type
        address_mode = user.address_mode or AddressMode.INFORMAL

        recent_rows = await self.generated_messages.list_recent_for_user(user.id)
        recent_messages = [
            RecentMessageContext(text=row.text, semantic_key=row.semantic_key)
            for row in recent_rows
            if row.text
        ][:MAX_RECENT_MESSAGES_IN_PROMPT]

        style_examples = [
            example.text for example in await self.style_examples.list_active_for_user(user.id)
        ][:MAX_LIKED_EXAMPLES_IN_PROMPT]

        reference_rows = await self.fallback_messages.list_active_for(
            topic_code, selected_type, address_mode
        )
        reference_examples = [
            ReferenceExample(text=row.text)
            for row in reference_rows[:MAX_REFERENCE_EXAMPLES_IN_PROMPT]
        ]

        request = GenerationRequest(
            address_mode=address_mode,
            message_type=selected_type,
            topic_code=topic_code,
            topic_label=topic_label,
            qualities=await self._load_quality_labels(user),
            support_preferences=await self._load_support_labels(user),
            blocked_topic_labels=await self._load_blocked_labels(user),
            style_examples=style_examples,
            reference_examples=reference_examples,
            recent_messages=recent_messages,
            recent_dislike_reasons=await self.feedback.list_recent_dislike_reasons(user.id),
        )
        return request, recent_messages

    async def _select_topic_and_type(self, user: User) -> tuple[str, str, MessageType]:
        """Тема — round-robin по порядку выбора в онбординге, тип чередуется
        compliment/support. Состояние не хранится отдельным полем, а
        выводится из последнего `GeneratedMessage` пользователя — проще, чем
        отдельная колонка, и не теряется, пока есть история сообщений."""
        active_topics = await self.user_topics.list_active_for_user(user.id)
        if not active_topics:
            raise GenerationError("у пользователя нет активных тем")

        topics_catalog = await self.topics.list_all()
        label_by_code = {t.code: t.label for t in topics_catalog}
        code_by_id = {t.id: t.code for t in topics_catalog}
        ordered_codes = [
            code_by_id[ut.topic_id] for ut in active_topics if ut.topic_id in code_by_id
        ]
        if not ordered_codes:
            raise GenerationError("активные темы пользователя отсутствуют в каталоге")

        last = await self.generated_messages.get_last_for_user(user.id)
        if last is None:
            topic_code = ordered_codes[0]
            message_type = random.choice(list(MessageType))
        else:
            if last.theme in ordered_codes:
                next_index = (ordered_codes.index(last.theme) + 1) % len(ordered_codes)
                topic_code = ordered_codes[next_index]
            else:
                topic_code = ordered_codes[0]
            message_type = (
                MessageType.SUPPORT
                if last.type == MessageType.COMPLIMENT
                else MessageType.COMPLIMENT
            )

        return topic_code, label_by_code[topic_code], message_type

    async def _load_quality_labels(self, user: User) -> list[str]:
        catalog = {q.id: q.label for q in await self.qualities.list_all()}
        labels = []
        for uq in await self.user_qualities.list_for_user(user.id):
            if uq.excluded_from_generation:
                continue
            if uq.quality_id is not None:
                labels.append(catalog.get(uq.quality_id, "?"))
            elif uq.custom_text:
                labels.append(uq.custom_text)
        return labels

    async def _load_support_labels(self, user: User) -> list[str]:
        catalog = dict(SUPPORT_PREFERENCE_OPTIONS)
        labels = []
        for sp in await self.support_preferences.list_for_user(user.id):
            if sp.excluded_from_generation:
                continue
            if sp.preference_code is not None:
                labels.append(catalog.get(sp.preference_code, "?"))
            elif sp.custom_text:
                labels.append(sp.custom_text)
        return labels

    async def _load_blocked_labels(self, user: User) -> list[str]:
        topics_catalog = {t.code: t.label for t in await self.topics.list_all()}
        labels = []
        for bt in await self.blocked_topics.list_for_user(user.id):
            if bt.topic_code is not None:
                labels.append(topics_catalog.get(bt.topic_code, bt.topic_code))
            elif bt.custom_text:
                labels.append(bt.custom_text)
        return labels

    async def _pick_fallback(
        self, request: GenerationRequest, recent_messages: list[RecentMessageContext]
    ) -> GenerationOutcome:
        candidates = await self.fallback_messages.list_active_for(
            request.topic_code, request.message_type, request.address_mode
        )
        if not candidates:
            candidates = await self.fallback_messages.list_active_for_any_topic(
                request.message_type, request.address_mode
            )
        if not candidates:
            raise GenerationError("нет резервных сообщений для данной темы/типа/обращения")

        used_keys = {m.semantic_key for m in recent_messages}
        unused = [c for c in candidates if c.semantic_key not in used_keys]
        chosen = random.choice(unused or candidates)

        return GenerationOutcome(
            text=chosen.text,
            message_type=chosen.type,
            theme=chosen.topic_code,
            semantic_key=chosen.semantic_key,
            source=MessageSource.FALLBACK,
            provider=None,
            model=None,
            input_tokens=None,
            output_tokens=None,
            total_tokens=None,
            prompt_version=None,
            validation_status="fallback",
        )
