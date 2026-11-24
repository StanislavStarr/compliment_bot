from app.domain.messages.enums import MessageType
from app.domain.users.enums import AddressMode
from app.infrastructure.ai.base import GenerationRequest, RecentMessageContext, ReferenceExample
from app.infrastructure.ai.prompts.builder import (
    build_system_prompt,
    build_user_input,
    prompt_version_for,
)


def _minimal_request() -> GenerationRequest:
    return GenerationRequest(
        address_mode=AddressMode.FORMAL,
        message_type=MessageType.SUPPORT,
        topic_code="self_confidence",
        topic_label="Уверенность в себе",
    )


def test_system_prompt_mentions_key_constraints() -> None:
    prompt = build_system_prompt(MessageType.COMPLIMENT)

    assert "русский" in prompt
    assert "эмодзи" in prompt
    assert "ПОЛЬЗОВАТЕЛЬСКИЕ ДАННЫЕ" in prompt
    assert "комплимент" in prompt.lower()


def test_support_prompt_differs_from_compliment() -> None:
    compliment = build_system_prompt(MessageType.COMPLIMENT)
    support = build_system_prompt(MessageType.SUPPORT)

    assert compliment != support
    assert "слова поддержки" in support
    assert "комплимент-похвалу" in support
    assert prompt_version_for(MessageType.COMPLIMENT) != prompt_version_for(MessageType.SUPPORT)
    assert "compliment" in prompt_version_for(MessageType.COMPLIMENT)
    assert "support" in prompt_version_for(MessageType.SUPPORT)


def test_user_input_reflects_formal_address_mode() -> None:
    text = build_user_input(_minimal_request())

    assert "на «вы»" in text
    assert "self_confidence" in text
    assert "support" in text
    assert "поддержку" in text


def test_compliment_user_input_omits_support_preferences() -> None:
    request = _minimal_request()
    request.message_type = MessageType.COMPLIMENT
    request.support_preferences = ["тёплые слова"]
    text = build_user_input(request)

    assert "поддержку" not in text
    assert "compliment" in text


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
