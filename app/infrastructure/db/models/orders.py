import uuid

from sqlalchemy import Boolean, Enum, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.domain.messages.enums import MessageType
from app.domain.orders.enums import InviteStatus, OrderStatus
from app.domain.users.enums import AddressMode
from app.infrastructure.db.base import Base, TimestampMixin, UUIDPkMixin


class Order(Base, UUIDPkMixin, TimestampMixin):
    __tablename__ = "orders"

    author_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    recipient_user_id: Mapped[uuid.UUID | None] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL")
    )
    recipient_username: Mapped[str | None] = mapped_column(String(64))

    status: Mapped[OrderStatus] = mapped_column(
        Enum(OrderStatus, name="order_status"), nullable=False, default=OrderStatus.DRAFT
    )
    message_type: Mapped[MessageType | None] = mapped_column(Enum(MessageType, name="message_type"))
    address_mode: Mapped[AddressMode | None] = mapped_column(Enum(AddressMode, name="address_mode"))
    portrait_notes: Mapped[str | None] = mapped_column(Text)
    sensitive_input_present: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)


class Invite(Base, UUIDPkMixin, TimestampMixin):
    __tablename__ = "invites"

    order_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("orders.id", ondelete="CASCADE"),
        unique=True,
        nullable=False,
    )
    token: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    status: Mapped[InviteStatus] = mapped_column(
        Enum(InviteStatus, name="invite_status"), nullable=False, default=InviteStatus.PENDING
    )


__all__ = ["Invite", "Order"]
