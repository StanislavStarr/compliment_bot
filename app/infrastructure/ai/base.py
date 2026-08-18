from dataclasses import dataclass, field
from typing import Protocol

from app.domain.messages.enums import MessageType
from app.domain.users.enums import AddressMode


@dataclass(frozen=True)
class RecentMessageContext:
    text: str
    semantic_key: str


@dataclass(frozen=True)
class ReferenceExample:
    """Эталонный пример темы — берётся из каталога `fallback_messages`
    (см. `FallbackMessageRepository`): та же таблица служит и few-shot
    референсом для промпта, и резервной фразой на случай отказа AI."""

    text: str


@dataclass
class GenerationRequest:
    """Обезличенный контекст для одного вызова провайдера. Telegram ID,
    username, chat ID, роль и город намеренно не включены — см. раздел
    "Данные, не передаваемые AI" продуктового плана."""

    address_mode: AddressMode
    message_type: MessageType
    topic_code: str
    topic_label: str

    qualities: list[str] = field(default_factory=list)
    support_preferences: list[str] = field(default_factory=list)
    blocked_topic_labels: list[str] = field(default_factory=list)
    style_examples: list[str] = field(default_factory=list)
    reference_examples: list[ReferenceExample] = field(default_factory=list)
    recent_messages: list[RecentMessageContext] = field(default_factory=list)
    recent_dislike_reasons: list[str] = field(default_factory=list)

    retry_reason: str | None = None


@dataclass
class AIGenerationResult:
    text: str
    message_type: MessageType
    theme: str
    semantic_key: str
    model: str
    input_tokens: int | None = None
    output_tokens: int | None = None
    total_tokens: int | None = None


class AIProviderError(Exception):
    """Техническая ошибка вызова провайдера (сеть, таймаут, 5xx, лимиты).
    Отличается от невалидного ответа — тот разбирается валидаторами, а не
    исключением. В Этапе 5 такие ошибки уйдут в retry Celery-таска."""


class AIProvider(Protocol):
    async def generate_message(self, request: GenerationRequest) -> AIGenerationResult: ...
