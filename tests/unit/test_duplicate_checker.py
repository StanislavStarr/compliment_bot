from app.domain.messages.enums import MessageType
from app.infrastructure.ai.base import AIGenerationResult, RecentMessageContext
from app.infrastructure.ai.validators.duplicate_checker import find_duplicate_reason


def _result(text: str, semantic_key: str = "новый смысловой ключ") -> AIGenerationResult:
    return AIGenerationResult(
        text=text,
        message_type=MessageType.COMPLIMENT,
        theme="self_confidence",
        semantic_key=semantic_key,
        model="gpt-4o-mini",
    )


def test_no_duplicate_when_no_recent_messages() -> None:
    assert find_duplicate_reason(_result("Уникальный текст сообщения."), []) is None


def test_exact_text_match_is_duplicate() -> None:
    recent = [
        RecentMessageContext(text="Ты справляешься лучше, чем думаешь!", semantic_key="другой ключ")
    ]
    result = _result("ты справляешься лучше, чем думаешь")

    reason = find_duplicate_reason(result, recent)

    assert reason is not None and "текстовое совпадение" in reason


def test_close_text_match_is_duplicate() -> None:
    recent = [
        RecentMessageContext(
            text="Ты справляешься лучше, чем сам думаешь, и это заметно окружающим.",
            semantic_key="другой ключ",
        )
    ]
    result = _result("Ты справляешься лучше, чем сам думаешь, и это очень заметно окружающим.")

    reason = find_duplicate_reason(result, recent)

    assert reason is not None


def test_semantic_key_match_is_duplicate() -> None:
    recent = [RecentMessageContext(text="Совсем другой текст.", semantic_key="ценность без идеала")]
    result = _result(
        "Абсолютно новый текст сообщения для проверки.", semantic_key="ценность без идеала"
    )

    reason = find_duplicate_reason(result, recent)

    assert reason is not None and "semantic_key" in reason


def test_different_message_is_not_duplicate() -> None:
    recent = [
        RecentMessageContext(text="Ты справляешься лучше, чем думаешь.", semantic_key="ключ один")
    ]
    result = _result(
        "Сегодня отличный день, чтобы заметить свои маленькие победы.", semantic_key="ключ два"
    )

    assert find_duplicate_reason(result, recent) is None
