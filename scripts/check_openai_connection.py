"""Разовая проверка связи с OpenAI: один вызов Responses API через тот же
`OpenAIProvider`, что использует приложение, с локальной валидацией ответа.

Использование:
    uv run python scripts/check_openai_connection.py

Требует непустой OPENAI_API_KEY в .env. Скрипт делает ровно один запрос."""

import asyncio

from app.config import get_settings
from app.domain.messages.enums import MessageType
from app.domain.users.enums import AddressMode
from app.infrastructure.ai.base import GenerationRequest
from app.infrastructure.ai.factory import create_ai_provider
from app.infrastructure.ai.validators.message_validator import validate_message


async def main() -> None:
    settings = get_settings()
    if not settings.openai_api_key.get_secret_value():
        print("OPENAI_API_KEY пуст в .env — заполните ключ и повторите запуск.")
        return

    provider = create_ai_provider(settings)
    request = GenerationRequest(
        address_mode=AddressMode.INFORMAL,
        message_type=MessageType.COMPLIMENT,
        topic_code="self_confidence",
        topic_label="Уверенность в себе",
        qualities=["упорство", "чувство юмора"],
        support_preferences=["тёплые слова поддержки"],
    )

    print(f"Модель: {settings.openai_model}")
    print("Отправляю один тестовый запрос...")
    result = await provider.generate_message(request)

    print("\n--- Ответ провайдера ---")
    print(f"text: {result.text}")
    print(f"type: {result.message_type}")
    print(f"theme: {result.theme}")
    print(f"semantic_key: {result.semantic_key}")
    print(f"tokens in/out: {result.input_tokens}/{result.output_tokens}")

    violations = validate_message(result, request)
    print("\n--- Локальная валидация ---")
    print("OK, нарушений нет" if not violations else f"Нарушения: {violations}")


if __name__ == "__main__":
    asyncio.run(main())
