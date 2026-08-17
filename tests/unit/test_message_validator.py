from app.domain.messages.enums import MessageType
from app.domain.users.enums import AddressMode
from app.infrastructure.ai.base import AIGenerationResult, GenerationRequest
from app.infrastructure.ai.validators.message_validator import validate_message

VALID_TEXT = (
    "Ты умеешь находить тепло даже в самых обычных днях, и это по-настоящему ценно, "
    "ведь такое качество редко встречается."
)


def _request(**overrides: object) -> GenerationRequest:
    defaults: dict[str, object] = {
        "address_mode": AddressMode.INFORMAL,
        "message_type": MessageType.COMPLIMENT,
        "topic_code": "self_confidence",
        "topic_label": "Уверенность в себе",
    }
    defaults.update(overrides)
    return GenerationRequest(**defaults)  # type: ignore[arg-type]


def _result(**overrides: object) -> AIGenerationResult:
    defaults: dict[str, object] = {
        "text": VALID_TEXT,
        "message_type": MessageType.COMPLIMENT,
        "theme": "self_confidence",
        "semantic_key": "тепло в обычных днях",
        "model": "gpt-4o-mini",
    }
    defaults.update(overrides)
    return AIGenerationResult(**defaults)  # type: ignore[arg-type]


def test_valid_message_has_no_violations() -> None:
    assert validate_message(_result(), _request()) == []


def test_too_short_text_is_rejected() -> None:
    violations = validate_message(_result(text="Коротко."), _request())
    assert any("длина текста" in v for v in violations)


def test_too_long_text_is_rejected() -> None:
    violations = validate_message(_result(text=VALID_TEXT * 5), _request())
    assert any("длина текста" in v for v in violations)


def test_too_many_sentences_is_rejected() -> None:
    text = "Это первое предложение. Это второе предложение. А это уже третье предложение тут."
    violations = validate_message(_result(text=text), _request())
    assert any("количество предложений" in v for v in violations)


def test_non_russian_text_is_rejected() -> None:
    text = "You are doing great and it truly matters, believe me, every single day of your life."
    violations = validate_message(_result(text=text), _request())
    assert any("не на русском" in v for v in violations)


def test_emoji_is_rejected() -> None:
    violations = validate_message(_result(text=VALID_TEXT + " 😊"), _request())
    assert any("эмодзи" in v for v in violations)


def test_greeting_is_rejected() -> None:
    violations = validate_message(_result(text="Привет! " + VALID_TEXT), _request())
    assert any("приветствие" in v for v in violations)


def test_advice_marker_is_rejected() -> None:
    text = "Попробуй чаще замечать, как много тепла ты приносишь в жизнь других людей."
    violations = validate_message(_result(text=text), _request())
    assert any("совет" in v for v in violations)


def test_theme_mismatch_is_rejected() -> None:
    violations = validate_message(_result(theme="career"), _request())
    assert any("тема ответа" in v for v in violations)


def test_type_mismatch_is_rejected() -> None:
    violations = validate_message(
        _result(message_type=MessageType.SUPPORT), _request(message_type=MessageType.COMPLIMENT)
    )
    assert any("тип ответа" in v for v in violations)


def test_empty_semantic_key_is_rejected() -> None:
    violations = validate_message(_result(semantic_key="  "), _request())
    assert any("semantic_key" in v for v in violations)
