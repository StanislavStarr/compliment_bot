from datetime import datetime

from sqlalchemy import BigInteger, Boolean, DateTime, Enum, String
from sqlalchemy.orm import Mapped, mapped_column

from app.domain.users.enums import (
    AuthorOnboardingStep,
    RecipientOnboardingStep,
    UserRole,
    UserStatus,
)
from app.infrastructure.db.base import Base, TimestampMixin, UUIDPkMixin


class User(Base, UUIDPkMixin, TimestampMixin):
    __tablename__ = "users"

    telegram_user_id: Mapped[int] = mapped_column(BigInteger, unique=True, nullable=False)
    telegram_chat_id: Mapped[int] = mapped_column(BigInteger, unique=True, nullable=False)
    telegram_username: Mapped[str | None] = mapped_column(String(64))

    role: Mapped[UserRole | None] = mapped_column(Enum(UserRole, name="user_role"))
    status: Mapped[UserStatus] = mapped_column(
        Enum(UserStatus, name="user_status"), nullable=False, default=UserStatus.ONBOARDING
    )
    author_step: Mapped[AuthorOnboardingStep | None] = mapped_column(
        Enum(AuthorOnboardingStep, name="author_onboarding_step")
    )
    recipient_step: Mapped[RecipientOnboardingStep | None] = mapped_column(
        Enum(RecipientOnboardingStep, name="recipient_onboarding_step")
    )
    language: Mapped[str] = mapped_column(String(8), nullable=False, default="ru")

    is_adult_confirmed: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    privacy_accepted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_seen_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


__all__ = ["User"]
