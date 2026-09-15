from dataclasses import dataclass
from enum import StrEnum


class NoticeKind(StrEnum):
    RECIPIENT_DECLINED = "recipient_declined"
    AUTHOR_CANCELLED = "author_cancelled"
    RECIPIENT_STOPPED = "recipient_stopped"


@dataclass(frozen=True)
class CounterpartNotice:
    """Порт наружу: application не шлёт в Telegram, роутер этапа 7 рендерит текст."""

    telegram_chat_id: int
    kind: NoticeKind
    author_username: str | None
    recipient_username: str | None
