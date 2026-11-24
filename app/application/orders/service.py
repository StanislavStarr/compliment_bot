from sqlalchemy.ext.asyncio import AsyncSession

from app.application.orders.notices import CounterpartNotice, NoticeKind
from app.domain.orders.enums import InviteStatus, OrderStatus
from app.domain.users.enums import UserStatus
from app.infrastructure.db.models.orders import Order
from app.infrastructure.db.models.users import User
from app.infrastructure.db.repositories.invites import InviteRepository
from app.infrastructure.db.repositories.orders import OrderRepository
from app.infrastructure.db.repositories.schedules import ScheduleRepository
from app.infrastructure.db.repositories.users import UserRepository


class OrderError(Exception):
    pass


class OpenOrderExistsError(OrderError):
    pass


class OrderService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self.orders = OrderRepository(session)
        self.invites = InviteRepository(session)
        self.users = UserRepository(session)
        self.schedules = ScheduleRepository(session)

    async def get_open_for_author(self, author: User) -> Order | None:
        return await self.orders.get_open_for_author(author.id)

    async def get_open_for_recipient(self, recipient: User) -> Order | None:
        return await self.orders.get_open_for_recipient(recipient.id)

    async def create_draft(self, author: User) -> Order:
        existing = await self.orders.get_open_for_author(author.id)
        if existing is not None:
            raise OpenOrderExistsError("у автора уже есть открытый заказ")
        order = await self.orders.create_draft(author.id)
        await self._session.commit()
        return order

    async def get_or_create_draft(self, author: User) -> Order:
        existing = await self.orders.get_open_for_author(author.id)
        if existing is not None:
            return existing
        order = await self.orders.create_draft(author.id)
        await self._session.flush()
        return order

    async def cancel(self, order: Order, *, initiated_by: NoticeKind) -> CounterpartNotice | None:
        if order.status is OrderStatus.CANCELLED:
            return None

        order.status = OrderStatus.CANCELLED
        invite = await self.invites.get_by_order_id(order.id)
        if invite is not None and invite.status is not InviteStatus.REVOKED:
            invite.status = InviteStatus.REVOKED

        if order.recipient_user_id is not None:
            schedule = await self.schedules.get_by_user_id(order.recipient_user_id)
            if schedule is not None:
                await self.schedules.pause(schedule)
            recipient = await self.users.get_by_id(order.recipient_user_id)
            if recipient is not None and recipient.status is UserStatus.ACTIVE:
                recipient.status = UserStatus.PAUSED

        notice = await self._notice_for(order, initiated_by)
        await self._session.commit()
        return notice

    async def _notice_for(self, order: Order, kind: NoticeKind) -> CounterpartNotice | None:
        if kind is NoticeKind.AUTHOR_CANCELLED:
            if order.recipient_user_id is None:
                return None
            recipient = await self.users.get_by_id(order.recipient_user_id)
            if recipient is None:
                return None
            author = await self.users.get_by_id(order.author_id)
            return CounterpartNotice(
                telegram_chat_id=recipient.telegram_chat_id,
                kind=kind,
                author_username=author.telegram_username if author else None,
                recipient_username=order.recipient_username,
            )

        author = await self.users.get_by_id(order.author_id)
        if author is None:
            return None
        return CounterpartNotice(
            telegram_chat_id=author.telegram_chat_id,
            kind=kind,
            author_username=author.telegram_username,
            recipient_username=order.recipient_username,
        )
