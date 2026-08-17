from app.config import Settings
from app.infrastructure.ai.base import AIProvider
from app.infrastructure.ai.providers.openai_provider import OpenAIProvider


def create_ai_provider(settings: Settings) -> AIProvider:
    return OpenAIProvider(
        api_key=settings.openai_api_key.get_secret_value(),
        model=settings.openai_model,
    )
