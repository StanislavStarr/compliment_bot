from openai import AsyncOpenAI, OpenAIError

from app.infrastructure.ai.base import AIGenerationResult, AIProviderError, GenerationRequest
from app.infrastructure.ai.prompts.builder import build_system_prompt, build_user_input
from app.infrastructure.ai.schemas import AIMessageSchema


class OpenAIProvider:
    """Единственное место в проекте, где импортируется SDK OpenAI — см.
    "SDK провайдера не импортируется вне infrastructure/ai/providers"."""

    def __init__(self, api_key: str, model: str) -> None:
        self._client = AsyncOpenAI(api_key=api_key)
        self._model = model

    async def generate_message(self, request: GenerationRequest) -> AIGenerationResult:
        try:
            response = await self._client.responses.parse(
                model=self._model,
                instructions=build_system_prompt(),
                input=build_user_input(request),
                text_format=AIMessageSchema,
                temperature=0.9,
                max_output_tokens=400,
            )
        except OpenAIError as exc:
            raise AIProviderError(f"{exc.__class__.__name__}: {exc}") from exc

        parsed = response.output_parsed
        if parsed is None:
            raise AIProviderError("Провайдер вернул пустой structured output")

        usage = response.usage
        return AIGenerationResult(
            text=parsed.text,
            message_type=parsed.type,
            theme=parsed.theme,
            semantic_key=parsed.semantic_key,
            model=self._model,
            input_tokens=usage.input_tokens if usage else None,
            output_tokens=usage.output_tokens if usage else None,
            total_tokens=usage.total_tokens if usage else None,
        )
