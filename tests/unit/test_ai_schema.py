import pytest
from pydantic import ValidationError

from app.domain.messages.enums import MessageType
from app.infrastructure.ai.schemas import AIMessageSchema


def test_structured_output_parses_valid_payload() -> None:
    parsed = AIMessageSchema.model_validate(
        {
            "text": "Ты умеешь замечать важное в обычном дне.",
            "type": "compliment",
            "theme": "self_confidence",
            "semantic_key": "тепло в обычных днях",
        }
    )

    assert parsed.type is MessageType.COMPLIMENT
    assert parsed.theme == "self_confidence"


def test_structured_output_rejects_unknown_type() -> None:
    with pytest.raises(ValidationError):
        AIMessageSchema.model_validate(
            {
                "text": "Ты умеешь замечать важное в обычном дне.",
                "type": "unknown",
                "theme": "self_confidence",
                "semantic_key": "тепло в обычных днях",
            }
        )


def test_structured_output_rejects_missing_fields() -> None:
    with pytest.raises(ValidationError):
        AIMessageSchema.model_validate({"text": "только текст"})
