import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, Enum, ForeignKey, Integer, Numeric, String, Text
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from app.domain.messages.enums import MessageSource, MessageType
from app.domain.users.enums import AddressMode
from app.infrastructure.db.base import Base, UUIDPkMixin


class PromptVersion(Base, UUIDPkMixin):
    __tablename__ = "prompt_versions"

    version: Mapped[str] = mapped_column(String(32), unique=True, nullable=False)
    system_prompt_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class GeneratedMessage(Base, UUIDPkMixin):
    __tablename__ = "generated_messages"

    delivery_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("deliveries.id", ondelete="CASCADE"),
        unique=True,
        nullable=False,
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )

    text: Mapped[str | None] = mapped_column(Text)
    type: Mapped[MessageType] = mapped_column(
        Enum(MessageType, name="message_type"), nullable=False
    )
    theme: Mapped[str] = mapped_column(String(64), nullable=False)
    semantic_key: Mapped[str] = mapped_column(String(255), nullable=False)

    source: Mapped[MessageSource] = mapped_column(
        Enum(MessageSource, name="message_source"), nullable=False
    )
    provider: Mapped[str | None] = mapped_column(String(64))
    model: Mapped[str | None] = mapped_column(String(64))
    prompt_version_id: Mapped[uuid.UUID | None] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("prompt_versions.id", ondelete="SET NULL")
    )

    input_tokens: Mapped[int | None] = mapped_column(Integer)
    output_tokens: Mapped[int | None] = mapped_column(Integer)
    total_tokens: Mapped[int | None] = mapped_column(Integer)
    estimated_cost: Mapped[float | None] = mapped_column(Numeric(10, 6))
    validation_status: Mapped[str | None] = mapped_column(String(32))

    generated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    sent_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    text_expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class FallbackMessage(Base, UUIDPkMixin):
    """Резервные фразы на случай отказа AI. Не привязаны к пользователю —
    общий каталог, сидируется в миграции по теме x типу x обращению."""

    __tablename__ = "fallback_messages"

    topic_code: Mapped[str] = mapped_column(String(64), nullable=False)
    type: Mapped[MessageType] = mapped_column(
        Enum(MessageType, name="message_type"), nullable=False
    )
    address_mode: Mapped[AddressMode] = mapped_column(
        Enum(AddressMode, name="address_mode"), nullable=False
    )
    text: Mapped[str] = mapped_column(Text, nullable=False)
    semantic_key: Mapped[str] = mapped_column(String(255), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)


__all__ = ["PromptVersion", "GeneratedMessage", "FallbackMessage"]
