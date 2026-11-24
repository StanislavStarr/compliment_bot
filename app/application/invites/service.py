import secrets
from dataclasses import dataclass

from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.orders.enums import InviteStatus, OrderStatus
from app.domain.users.usernames import normalize_telegram_username
from app.infrastructure.db.models.orders import Invite, Order
from app.infrastructure.db.repositories.invites import InviteRepository
from app.infrastructure.db.repositories.orders import OrderRepository

INVITE_PAYLOAD_PREFIX = "inv_"


class InviteError(Exception):
    pass


class InviteNotFoundError(InviteError):
    pass


class InviteNotPendingError(InviteError):
    pass


class UsernameMissingError(InviteError):
    pass


class UsernameMismatchError(InviteError):
    pass


class InviteNotReadyError(InviteError):
    pass


@dataclass(frozen=True)
class IssuedInvite:
    token: str
    link: str


def parse_invite_payload(payload: str) -> str | None:
    raw = payload.strip()
    if raw.startswith("/start"):
        parts = raw.split(maxsplit=1)
        if len(parts) < 2:
            return None
        raw = parts[1]
    if not raw.startswith(INVITE_PAYLOAD_PREFIX):
        return None
    token = raw[len(INVITE_PAYLOAD_PREFIX) :]
    return token or None


def build_invite_link(bot_username: str, token: str) -> str:
    username = bot_username.lstrip("@")
    return f"https://t.me/{username}?start={INVITE_PAYLOAD_PREFIX}{token}"


class InviteService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self.invites = InviteRepository(session)
        self.orders = OrderRepository(session)

    async def issue(self, order: Order, bot_username: str) -> IssuedInvite:
        if not normalize_telegram_username(order.recipient_username):
            raise InviteNotReadyError("не указан username адресата")
        if order.message_type is None or order.address_mode is None:
            raise InviteNotReadyError("не заполнены жанр или обращение")
        if order.status is OrderStatus.CANCELLED:
            raise InviteNotReadyError("заказ отменён")

        invite = await self.invites.get_by_order_id(order.id)
        if invite is None:
            invite = await self.invites.create(order.id, secrets.token_urlsafe(16))
        elif invite.status is not InviteStatus.PENDING:
            raise InviteNotPendingError("инвайт уже использован или отозван")

        order.status = OrderStatus.PENDING
        await self._session.commit()
        return IssuedInvite(token=invite.token, link=build_invite_link(bot_username, invite.token))

    async def resolve(self, payload: str, telegram_username: str | None) -> tuple[Invite, Order]:
        token = parse_invite_payload(payload)
        if token is None:
            raise InviteNotFoundError("нет токена приглашения")

        invite = await self.invites.get_by_token(token)
        if invite is None:
            raise InviteNotFoundError("приглашение не найдено")
        if invite.status is not InviteStatus.PENDING:
            raise InviteNotPendingError("приглашение уже не активно")

        order = await self.orders.get_by_id(invite.order_id)
        if order is None or order.status is not OrderStatus.PENDING:
            raise InviteNotFoundError("заказ к приглашению не найден")

        actual = normalize_telegram_username(telegram_username)
        if actual is None:
            raise UsernameMissingError("у адресата нет username")
        expected = normalize_telegram_username(order.recipient_username)
        if expected is None or actual != expected:
            raise UsernameMismatchError("username не совпадает с приглашением")

        return invite, order
