import re

from app.domain.messages.constants import MAX_MESSAGE_LENGTH, MAX_SENTENCES, MIN_MESSAGE_LENGTH
from app.infrastructure.ai.base import AIGenerationResult, GenerationRequest

_EMOJI_PATTERN = re.compile(
    "["
    "\U0001f300-\U0001fad6"
    "\U00002600-\U000027bf"
    "\U0001f1e6-\U0001f1ff"
    "\U00002190-\U000021ff"
    "\U00002700-\U000027bf"
    "]"
)
_SENTENCE_SPLIT_PATTERN = re.compile(r"[.!?…]+")
_CYRILLIC_PATTERN = re.compile(r"[а-яА-ЯёЁ]")
_LATIN_PATTERN = re.compile(r"[a-zA-Z]")

# Список нарочно небольшой и эвристический — точная детекция тона/советов
# на regex-правилах не решается, это осознанное упрощение MVP. Более строгую
# проверку можно добавить позже (например, отдельным вызовом модели-судьи).
_GREETING_MARKERS = ("привет", "здравств", "добрый день", "доброе утро", "добрый вечер")
_ADVICE_MARKERS = (
    "попробуй",
    "попробуйте",
    "стоит ",
    "нужно ",
    "необходимо ",
    "советую",
    "рекомендую",
    "постарайся",
    "постарайтесь",
)


def _count_sentences(text: str) -> int:
    parts = [p for p in _SENTENCE_SPLIT_PATTERN.split(text) if p.strip()]
    return len(parts)


def _is_russian(text: str) -> bool:
    cyrillic = len(_CYRILLIC_PATTERN.findall(text))
    latin = len(_LATIN_PATTERN.findall(text))
    return cyrillic > 0 and cyrillic >= latin * 3


def validate_message(result: AIGenerationResult, request: GenerationRequest) -> list[str]:
    """Возвращает список нарушений локальной валидации (раздел 13 плана).
    Пустой список — сообщение прошло проверку."""
    text = result.text.strip()
    violations: list[str] = []

    if not (MIN_MESSAGE_LENGTH <= len(text) <= MAX_MESSAGE_LENGTH):
        violations.append(
            f"длина текста {len(text)} вне диапазона {MIN_MESSAGE_LENGTH}-{MAX_MESSAGE_LENGTH}"
        )

    sentence_count = _count_sentences(text)
    if sentence_count == 0 or sentence_count > MAX_SENTENCES:
        violations.append(
            f"количество предложений {sentence_count} вне диапазона 1-{MAX_SENTENCES}"
        )

    if not _is_russian(text):
        violations.append("текст не на русском языке")

    if _EMOJI_PATTERN.search(text):
        violations.append("текст содержит эмодзи")

    lowered = text.lower()
    if any(marker in lowered for marker in _GREETING_MARKERS):
        violations.append("текст содержит приветствие")

    if any(marker in lowered for marker in _ADVICE_MARKERS):
        violations.append("текст похож на совет или призыв к действию")

    if result.theme != request.topic_code:
        violations.append(
            f"тема ответа '{result.theme}' не совпадает с запрошенной '{request.topic_code}'"
        )

    if result.message_type != request.message_type:
        violations.append(
            f"тип ответа '{result.message_type}' не совпадает с запрошенным '{request.message_type}'"
        )

    if not result.semantic_key.strip() or len(result.semantic_key) > 100:
        violations.append("semantic_key пустой или слишком длинный")

    return violations
