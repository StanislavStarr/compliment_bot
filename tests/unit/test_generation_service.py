from typing import Any
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

from app.application.generation.service import GenerationService
from app.domain.messages.enums import MessageSource, MessageType
from app.domain.users.enums import AddressMode
from app.infrastructure.ai.base import AIGenerationResult, AIProviderError

VALID_TEXT = (
    "Ты умеешь находить тепло даже в самых обычных днях, и это по-настоящему ценно, "
    "ведь такое качество редко встречается."
)


class ScriptedProvider:
    def __init__(self, responses: list[AIGenerationResult | Exception]) -> None:
        self._responses = list(responses)
        self.calls = 0

    async def generate_message(self, request: object) -> AIGenerationResult:
        self.calls += 1
        item = self._responses.pop(0)
        if isinstance(item, Exception):
            raise item
        return item


def _ok_result(*, theme: str = "self_confidence") -> AIGenerationResult:
    return AIGenerationResult(
        text=VALID_TEXT,
        message_type=MessageType.COMPLIMENT,
        theme=theme,
        semantic_key="тепло в обычных днях",
        model="gpt-4o-mini",
        input_tokens=11,
        output_tokens=22,
        total_tokens=33,
    )


def _invalid_result(*, theme: str = "self_confidence") -> AIGenerationResult:
    return AIGenerationResult(
        text="Коротко.",
        message_type=MessageType.COMPLIMENT,
        theme=theme,
        semantic_key="коротко",
        model="gpt-4o-mini",
    )


def _service(provider: ScriptedProvider) -> tuple[GenerationService, MagicMock]:
    session = AsyncMock()
    service = GenerationService(session, provider)
    topic_id = uuid4()
    topic = MagicMock()
    topic.id = topic_id
    topic.code = "self_confidence"
    topic.label = "Уверенность в себе"
    user_topic = MagicMock()
    user_topic.topic_id = topic_id

    fallback = MagicMock()
    fallback.text = VALID_TEXT
    fallback.type = MessageType.COMPLIMENT
    fallback.topic_code = "self_confidence"
    fallback.semantic_key = "резервная фраза спокойствия"

    topics = AsyncMock()
    topics.list_all.return_value = [topic]
    user_topics = AsyncMock()
    user_topics.list_active_for_user.return_value = [user_topic]
    generated = AsyncMock()
    generated.list_recent_for_user.return_value = []
    generated.get_last_for_user.return_value = None
    style = AsyncMock()
    style.list_active_for_user.return_value = []
    fallbacks = AsyncMock()
    fallbacks.list_active_for.return_value = [fallback]
    fallbacks.list_active_for_any_topic.return_value = [fallback]
    qualities = AsyncMock()
    qualities.list_all.return_value = []
    user_qualities = AsyncMock()
    user_qualities.list_for_user.return_value = []
    support = AsyncMock()
    support.list_for_user.return_value = []
    blocked = AsyncMock()
    blocked.list_for_user.return_value = []
    feedback = AsyncMock()
    feedback.list_recent_dislike_reasons.return_value = []

    bind: Any = service
    bind.topics = topics
    bind.user_topics = user_topics
    bind.generated_messages = generated
    bind.style_examples = style
    bind.fallback_messages = fallbacks
    bind.qualities = qualities
    bind.user_qualities = user_qualities
    bind.support_preferences = support
    bind.blocked_topics = blocked
    bind.feedback = feedback

    user = MagicMock()
    user.id = uuid4()
    user.address_mode = AddressMode.INFORMAL
    return service, user


async def test_valid_ai_result_is_used_without_retry() -> None:
    provider = ScriptedProvider([_ok_result()])
    service, user = _service(provider)

    outcome = await service.generate_via_ai_or_raise(user, message_type=MessageType.COMPLIMENT)

    assert outcome.source is MessageSource.AI
    assert outcome.text == VALID_TEXT
    assert provider.calls == 1


async def test_invalid_output_triggers_corrective_regeneration() -> None:
    provider = ScriptedProvider([_invalid_result(), _ok_result()])
    service, user = _service(provider)

    outcome = await service.generate_via_ai_or_raise(user, message_type=MessageType.COMPLIMENT)

    assert outcome.source is MessageSource.AI
    assert provider.calls == 2


async def test_two_invalid_outputs_fall_back() -> None:
    provider = ScriptedProvider([_invalid_result(), _invalid_result()])
    service, user = _service(provider)

    outcome = await service.generate_via_ai_or_raise(user, message_type=MessageType.COMPLIMENT)

    assert outcome.source is MessageSource.FALLBACK
    assert outcome.validation_status == "fallback"
    assert provider.calls == 2


async def test_provider_error_falls_back_in_generate() -> None:
    provider = ScriptedProvider([AIProviderError("timeout")])
    service, user = _service(provider)

    outcome = await service.generate(user, message_type=MessageType.COMPLIMENT)

    assert outcome.source is MessageSource.FALLBACK
    assert provider.calls == 1
