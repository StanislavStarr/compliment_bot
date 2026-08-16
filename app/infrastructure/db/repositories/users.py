from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.infrastructure.db.models.users import User


class UserRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_telegram_id(self, telegram_user_id: int) -> User | None:
        result = await self._session.execute(
            select(User).where(User.telegram_user_id == telegram_user_id)
        )
        return result.scalar_one_or_none()

    async def create(self, telegram_user_id: int, telegram_chat_id: int) -> User:
        user = User(telegram_user_id=telegram_user_id, telegram_chat_id=telegram_chat_id)
        self._session.add(user)
        await self._session.flush()
        return user
