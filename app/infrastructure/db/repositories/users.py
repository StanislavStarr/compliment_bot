import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.users.enums import (
    AuthorOnboardingStep,
    RecipientOnboardingStep,
    UserRole,
    UserStatus,
)
from app.infrastructure.db.models.users import User


class UserRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_id(self, user_id: uuid.UUID) -> User | None:
        return await self._session.get(User, user_id)

    async def get_by_telegram_id(self, telegram_user_id: int) -> User | None:
        result = await self._session.execute(
            select(User).where(User.telegram_user_id == telegram_user_id)
        )
        return result.scalar_one_or_none()

    async def create(
        self,
        telegram_user_id: int,
        telegram_chat_id: int,
        *,
        telegram_username: str | None = None,
        role: UserRole | None = None,
        author_step: AuthorOnboardingStep | None = None,
        recipient_step: RecipientOnboardingStep | None = None,
    ) -> User:
        user = User(
            telegram_user_id=telegram_user_id,
            telegram_chat_id=telegram_chat_id,
            telegram_username=telegram_username,
            role=role,
            author_step=author_step,
            recipient_step=recipient_step,
        )
        self._session.add(user)
        await self._session.flush()
        return user

    async def mark_blocked(self, user: User) -> None:
        """Telegram вернул Forbidden (пользователь заблокировал бота) —
        останавливаем доставки без бесконечных retries (раздел 17 плана)."""
        user.status = UserStatus.BLOCKED
        await self._session.flush()

    async def delete(self, user: User) -> None:
        await self._session.delete(user)
        await self._session.flush()
