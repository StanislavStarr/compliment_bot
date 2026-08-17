"""Константы генерации и валидации сообщений. Вынесены отдельно от enums,
т.к. это не категориальные значения, а пороги/версии, которые могут меняться
чаще (например, при подборе промпта — см. раздел 13 продуктового плана)."""

CURRENT_PROMPT_VERSION = "v1"

MIN_MESSAGE_LENGTH = 80
MAX_MESSAGE_LENGTH = 250
MAX_SENTENCES = 2

MAX_RECENT_MESSAGES_IN_PROMPT = 15
MAX_LIKED_EXAMPLES_IN_PROMPT = 5
MAX_REFERENCE_EXAMPLES_IN_PROMPT = 3
MAX_RECENT_DISLIKE_REASONS_IN_PROMPT = 5

DUPLICATE_TEXT_SIMILARITY_THRESHOLD = 0.9
