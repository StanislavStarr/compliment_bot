import uuid

from sqlalchemy import Boolean, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.infrastructure.db.base import Base, TimestampMixin, UUIDPkMixin


class Topic(Base, UUIDPkMixin):
    """Справочник тем. Код (`self_confidence`, ...) — строка, а не Postgres ENUM,
    чтобы можно было добавлять темы без миграции схемы."""

    __tablename__ = "topics"

    code: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    label: Mapped[str] = mapped_column(String(255), nullable=False)


class UserTopic(Base, UUIDPkMixin, TimestampMixin):
    __tablename__ = "user_topics"
    __table_args__ = (UniqueConstraint("user_id", "topic_id", name="uq_user_topics_user_topic"),)

    user_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    topic_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("topics.id", ondelete="RESTRICT"), nullable=False
    )
    position: Mapped[int] = mapped_column(Integer, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)


__all__ = ["Topic", "UserTopic"]
