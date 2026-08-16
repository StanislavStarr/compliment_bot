from datetime import datetime

from sqlalchemy import BigInteger, Boolean, DateTime, Enum, String
from sqlalchemy.orm import Mapped, mapped_column

from app.domain.users.enums import AddressMode, OnboardingStep, UserStatus
from app.infrastructure.db.base import Base, TimestampMixin, UUIDPkMixin


class User(Base, UUIDPkMixin, TimestampMixin):
    __tablename__ = "users"

    telegram_user_id: Mapped[int] = mapped_column(BigInteger, unique=True, nullable=False)
    telegram_chat_id: Mapped[int] = mapped_column(BigInteger, unique=True, nullable=False)

    status: Mapped[UserStatus] = mapped_column(
        Enum(UserStatus, name="user_status"), nullable=False, default=UserStatus.ONBOARDING
    )
    onboarding_step: Mapped[OnboardingStep | None] = mapped_column(
        Enum(OnboardingStep, name="onboarding_step"), nullable=True
    )
    address_mode: Mapped[AddressMode | None] = mapped_column(
        Enum(AddressMode, name="address_mode"), nullable=True
    )
    language: Mapped[str] = mapped_column(String(8), nullable=False, default="ru")

    is_adult_confirmed: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    privacy_accepted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_seen_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


__all__ = ["User"]
