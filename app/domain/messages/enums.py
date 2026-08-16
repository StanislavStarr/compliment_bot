from enum import StrEnum


class MessageType(StrEnum):
    COMPLIMENT = "compliment"
    SUPPORT = "support"


class MessageSource(StrEnum):
    AI = "ai"
    FALLBACK = "fallback"
