from pydantic import BaseModel, Field

from app.domain.messages.enums import MessageType


class AIMessageSchema(BaseModel):
    """Structured output модели. Поля соответствуют формату из раздела
    13 продуктового плана. Схема отдаётся провайдеру напрямую (Structured
    Outputs), поэтому лишних полей и свободной вложенности быть не должно."""

    text: str = Field(description="Готовый текст комплимента или поддержки на русском языке")
    type: MessageType = Field(description="Тип сообщения — должен совпадать с запрошенным")
    theme: str = Field(description="Код темы — должен совпадать с запрошенной темой")
    semantic_key: str = Field(
        description="Короткая фраза (3-6 слов), описывающая смысловое ядро сообщения — "
        "используется для защиты от повторов"
    )
