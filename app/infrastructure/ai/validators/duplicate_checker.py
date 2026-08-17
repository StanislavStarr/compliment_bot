import re
from difflib import SequenceMatcher

from app.domain.messages.constants import DUPLICATE_TEXT_SIMILARITY_THRESHOLD
from app.infrastructure.ai.base import AIGenerationResult, RecentMessageContext

_WHITESPACE_PATTERN = re.compile(r"\s+")
_PUNCTUATION_PATTERN = re.compile(r"[^\w\s]", re.UNICODE)


def _normalize(text: str) -> str:
    text = text.lower().strip()
    text = _PUNCTUATION_PATTERN.sub("", text)
    return _WHITESPACE_PATTERN.sub(" ", text)


def find_duplicate_reason(
    result: AIGenerationResult, recent_messages: list[RecentMessageContext]
) -> str | None:
    """Простейшая защита от повторов без embeddings (раздел 12 плана):
    exact match, близкое текстовое совпадение и совпадение semantic_key.
    Возвращает причину или None, если повтора не найдено."""
    normalized_candidate = _normalize(result.text)
    candidate_key = result.semantic_key.strip().lower()

    for message in recent_messages:
        if message.semantic_key.strip().lower() == candidate_key:
            return f"semantic_key совпадает с недавним сообщением: '{message.semantic_key}'"

        normalized_recent = _normalize(message.text)
        if normalized_candidate == normalized_recent:
            return "точное текстовое совпадение с недавним сообщением"

        similarity = SequenceMatcher(None, normalized_candidate, normalized_recent).ratio()
        if similarity >= DUPLICATE_TEXT_SIMILARITY_THRESHOLD:
            return f"текст слишком похож на недавнее сообщение (similarity={similarity:.2f})"

    return None
