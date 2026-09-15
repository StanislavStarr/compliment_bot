from datetime import UTC, datetime, time

from sqlalchemy.ext.asyncio import AsyncSession

from app.application.orders.notices import CounterpartNotice, NoticeKind
from app.application.orders.service import OpenOrderExistsError, OrderService
from app.application.scheduling.calculator import compute_next_run
from app.domain.orders.enums import InviteStatus, OrderStatus
from app.domain.schedules.enums import Period, ScheduleMode
from app.domain.users.enums import RecipientOnboardingStep, UserRole, UserStatus
from app.domain.users.usernames import normalize_telegram_username
from app.infrastructure.db.models.orders import Invite, Order
from app.infrastructure.db.models.users import User
from app.infrastructure.db.repositories.invites import InviteRepository
from app.infrastructure.db.repositories.orders import OrderRepository
from app.infrastructure.db.repositories.profiles import ProfileRepository
from app.infrastructure.db.repositories.schedules import ScheduleRepository
from app.infrastructure.db.repositories.users import UserRepository


class RecipientOnboardingError(Exception):
    pass


class RecipientOnboardingService:
    """Онбординг адресата: согласие и слот. Портрет не копируется."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self.users = UserRepository(session)
        self.profiles = ProfileRepository(session)
        self.orders = OrderRepository(session)
        self.invites = InviteRepository(session)
        self.schedules = ScheduleRepository(session)
        self.order_service = OrderService(session)

    async def get_or_create_user(
        self,
        telegram_user_id: int,
        telegram_chat_id: int,
        telegram_username: str | None = None,
    ) -> User:
        username = normalize_telegram_username(telegram_username)
        user = await self.users.get_by_telegram_id(telegram_user_id)
        if user is not None:
            user.last_seen_at = datetime.now(UTC)
            user.telegram_username = username
            await self._session.commit()
            return user
        user = await self.users.create(
            telegram_user_id,
            telegram_chat_id,
            telegram_username=username,
            role=UserRole.RECIPIENT,
            recipient_step=RecipientOnboardingStep.CONSENT,
        )
        await self.profiles.get_or_create(user.id)
        await self._session.commit()
        return user

    async def set_step(self, recipient: User, step: RecipientOnboardingStep) -> None:
        recipient.recipient_step = step
        await self._session.commit()

    async def confirm_consent(self, recipient: User) -> None:
        recipient.is_adult_confirmed = True
        recipient.privacy_accepted_at = datetime.now(UTC)
        await self._session.commit()

    async def accept(self, invite: Invite, order: Order, recipient: User) -> None:
        if recipient.id == order.author_id:
            raise RecipientOnboardingError("нельзя принять собственное приглашение")
        existing = await self.orders.get_open_for_recipient(recipient.id)
        if existing is not None and existing.id != order.id:
            raise OpenOrderExistsError("адресат уже связан с другим заказом")

        invite.status = InviteStatus.ACCEPTED
        order.recipient_user_id = recipient.id
        recipient.role = UserRole.RECIPIENT
        recipient.recipient_step = RecipientOnboardingStep.TIMEZONE
        await self._session.commit()

    async def decline(self, order: Order) -> CounterpartNotice | None:
        return await self.order_service.cancel(order, initiated_by=NoticeKind.RECIPIENT_DECLINED)

    async def finalize_schedule(
        self,
        recipient: User,
        order: Order,
        timezone_name: str,
        mode: ScheduleMode,
        exact_local_time: time | None = None,
        period: Period | None = None,
    ) -> None:
        if order.recipient_user_id != recipient.id:
            raise RecipientOnboardingError("заказ не привязан к этому адресату")
        next_run_at_utc = compute_next_run(
            datetime.now(UTC), timezone_name, mode, exact_local_time, period
        )
        await self.schedules.upsert(
            user_id=recipient.id,
            mode=mode,
            timezone_name=timezone_name,
            next_run_at_utc=next_run_at_utc,
            exact_local_time=exact_local_time,
            period=period,
            order_id=order.id,
        )
        await self._session.commit()

    async def complete(self, recipient: User, order: Order) -> None:
        if order.recipient_user_id != recipient.id:
            raise RecipientOnboardingError("заказ не привязан к этому адресату")
        schedule = await self.schedules.get_by_user_id(recipient.id)
        if schedule is None:
            raise RecipientOnboardingError("сначала выберите время получения")
        order.status = OrderStatus.ACTIVE
        recipient.status = UserStatus.ACTIVE
        recipient.recipient_step = RecipientOnboardingStep.DONE
        await self._session.commit()
