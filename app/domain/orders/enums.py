from enum import StrEnum

__all__ = [
    "InviteStatus",
    "OPEN_ORDER_STATUSES",
    "OrderStatus",
]


class OrderStatus(StrEnum):
    DRAFT = "draft"
    PENDING = "pending"
    ACTIVE = "active"
    CANCELLED = "cancelled"


class InviteStatus(StrEnum):
    PENDING = "pending"
    ACCEPTED = "accepted"
    REVOKED = "revoked"


OPEN_ORDER_STATUSES: tuple[OrderStatus, ...] = (
    OrderStatus.DRAFT,
    OrderStatus.PENDING,
    OrderStatus.ACTIVE,
)
