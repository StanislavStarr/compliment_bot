import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.orders.enums import InviteStatus
from app.infrastructure.db.models.orders import Invite


class InviteRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_token(self, token: str) -> Invite | None:
        result = await self._session.execute(select(Invite).where(Invite.token == token))
        return result.scalar_one_or_none()

    async def get_by_order_id(self, order_id: uuid.UUID) -> Invite | None:
        result = await self._session.execute(select(Invite).where(Invite.order_id == order_id))
        return result.scalar_one_or_none()

    async def create(self, order_id: uuid.UUID, token: str) -> Invite:
        invite = Invite(order_id=order_id, token=token, status=InviteStatus.PENDING)
        self._session.add(invite)
        await self._session.flush()
        return invite
