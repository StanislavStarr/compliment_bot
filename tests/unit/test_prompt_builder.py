from app.domain.messages.enums import MessageType
from app.domain.users.enums import AddressMode
from app.infrastructure.ai.base import GenerationRequest, RecentMessageContext, ReferenceExample
from app.infrastructure.ai.prompts.builder import build_system_prompt, build_user_input


def _minimal_request() -> GenerationRequest:
    return GenerationRequest(
        address_mode=AddressMode.FORMAL,
        message_type=MessageType.SUPPORT,
        topic_code="self_confidence",
        topic_label="Уверенность в себе",
    )


def test_system_prompt_mentions_key_constraints() -> None:
    prompt = build_system_prompt()

    assert "русский" in prompt
    assert "эмодзи" in prompt
    assert "ПОЛЬЗОВАТЕЛЬСКИЕ ДАННЫЕ" in prompt


def test_user_input_reflects_formal_address_mode() -> None:
    text = build_user_input(_minimal_request())

    assert "на «вы»" in text
    assert "self_confidence" in text
    assert "support" in text


def test_user_input_includes_optional_sections_when_present() -> None:
    request = _minimal_request()
    request.qualities = ["доброта"]
    request.support_preferences = ["тёплые слова"]
    request.blocked_topic_labels = ["Работа"]
    request.style_examples = ["Пример понравившейся фразы."]
    request.reference_examples = [ReferenceExample(text="Эталонный пример темы.")]
    request.recent_messages = [
        RecentMessageContext(text="Старое сообщение.", semantic_key="старый ключ")
    ]
    request.recent_dislike_reasons = ["слишком общее"]
    request.retry_reason = "нарушена длина текста"

    text = build_user_input(request)

    assert "Работа" in text
    assert "Пример понравившейся фразы." in text
    assert "Эталонный пример темы." in text
    assert "Старое сообщение." in text
    assert "слишком общее" in text
    assert "нарушена длина текста" in text


def test_user_input_omits_optional_sections_when_absent() -> None:
    text = build_user_input(_minimal_request())

    assert "Нежелательные" not in text
    assert "Уточнение" not in text
