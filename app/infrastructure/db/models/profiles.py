import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, Enum, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from app.domain.profiles.enums import StyleExampleSource
from app.infrastructure.db.base import Base, TimestampMixin, UUIDPkMixin


class Profile(Base, TimestampMixin):
    """Один профиль на пользователя. Имя не хранится — не используется в генерации."""

    __tablename__ = "profiles"

    user_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), primary_key=True
    )
    support_description: Mapped[str | None] = mapped_column(Text)
    sensitive_input_present: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)


class Quality(Base, UUIDPkMixin):
    """Справочник готовых качеств для шага онбординга."""

    __tablename__ = "qualities"

    code: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    label: Mapped[str] = mapped_column(String(255), nullable=False)


class UserQuality(Base, UUIDPkMixin, TimestampMixin):
    __tablename__ = "user_qualities"

    user_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    quality_id: Mapped[uuid.UUID | None] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("qualities.id", ondelete="RESTRICT"), nullable=True
    )
    custom_text: Mapped[str | None] = mapped_column(Text)
    is_sensitive: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    excluded_from_generation: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)


class SupportPreference(Base, UUIDPkMixin, TimestampMixin):
    __tablename__ = "support_preferences"

    user_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    preference_code: Mapped[str | None] = mapped_column(String(64))
    custom_text: Mapped[str | None] = mapped_column(Text)
    is_sensitive: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    excluded_from_generation: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)


class BlockedTopic(Base, UUIDPkMixin, TimestampMixin):
    """Нежелательные темы. `topic_code` — свободная строка, а не FK на `topics`:
    пользователь может заблокировать тему, которой нет в справочнике."""

    __tablename__ = "blocked_topics"

    user_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    topic_code: Mapped[str | None] = mapped_column(String(64))
    custom_text: Mapped[str | None] = mapped_column(Text)
    is_sensitive: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)


class StyleExample(Base, UUIDPkMixin):
    __tablename__ = "style_examples"

    user_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    text: Mapped[str] = mapped_column(Text, nullable=False)
    source: Mapped[StyleExampleSource] = mapped_column(
        Enum(StyleExampleSource, name="style_example_source"), nullable=False
    )
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


__all__ = [
    "Profile",
    "Quality",
    "UserQuality",
    "SupportPreference",
    "BlockedTopic",
    "StyleExample",
]
