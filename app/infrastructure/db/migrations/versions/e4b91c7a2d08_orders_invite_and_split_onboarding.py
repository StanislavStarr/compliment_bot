"""orders, invites, split onboarding steps

Revision ID: e4b91c7a2d08
Revises: a1c7e3f9b2d4
Create Date: 2026-09-13 22:40:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import ENUM as PG_ENUM

revision: str = "e4b91c7a2d08"
down_revision: str | Sequence[str] | None = "a1c7e3f9b2d4"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

user_role = PG_ENUM("AUTHOR", "RECIPIENT", name="user_role", create_type=False)
author_onboarding_step = PG_ENUM(
    "CONSENT",
    "GENRE",
    "RECIPIENT_USERNAME",
    "ADDRESS_MODE",
    "QUALITIES",
    "TOPICS",
    "SUPPORT_PREFERENCES",
    "BLOCKED_TOPICS",
    "STYLE_EXAMPLES",
    "PORTRAIT_NOTES",
    "SUMMARY",
    "DONE",
    "TIMEZONE",
    "SCHEDULE_MODE",
    "SCHEDULE_TIME",
    name="author_onboarding_step",
    create_type=False,
)
recipient_onboarding_step = PG_ENUM(
    "CONSENT",
    "TIMEZONE",
    "SCHEDULE_MODE",
    "SCHEDULE_TIME",
    "DONE",
    name="recipient_onboarding_step",
    create_type=False,
)
order_status = PG_ENUM(
    "DRAFT", "PENDING", "ACTIVE", "CANCELLED", name="order_status", create_type=False
)
invite_status = PG_ENUM("PENDING", "ACCEPTED", "REVOKED", name="invite_status", create_type=False)
address_mode = PG_ENUM("INFORMAL", "FORMAL", name="address_mode", create_type=False)
message_type = PG_ENUM("COMPLIMENT", "SUPPORT", name="message_type", create_type=False)


def upgrade() -> None:
    # Старые профили «сам себе» в A→B не мапятся.
    op.execute("DELETE FROM users")

    bind = op.get_bind()
    user_role.create(bind, checkfirst=True)
    author_onboarding_step.create(bind, checkfirst=True)
    recipient_onboarding_step.create(bind, checkfirst=True)
    order_status.create(bind, checkfirst=True)
    invite_status.create(bind, checkfirst=True)

    op.add_column("users", sa.Column("telegram_username", sa.String(length=64), nullable=True))
    op.add_column("users", sa.Column("role", user_role, nullable=True))
    op.add_column("users", sa.Column("author_step", author_onboarding_step, nullable=True))
    op.add_column("users", sa.Column("recipient_step", recipient_onboarding_step, nullable=True))
    op.drop_column("users", "onboarding_step")
    op.drop_column("users", "address_mode")
    op.execute("DROP TYPE onboarding_step")

    op.create_table(
        "orders",
        sa.Column("author_id", sa.UUID(), nullable=False),
        sa.Column("recipient_user_id", sa.UUID(), nullable=True),
        sa.Column("recipient_username", sa.String(length=64), nullable=True),
        sa.Column("status", order_status, nullable=False),
        sa.Column("message_type", message_type, nullable=True),
        sa.Column("address_mode", address_mode, nullable=True),
        sa.Column("portrait_notes", sa.Text(), nullable=True),
        sa.Column("sensitive_input_present", sa.Boolean(), nullable=False),
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["author_id"],
            ["users.id"],
            name=op.f("fk_orders_author_id_users"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["recipient_user_id"],
            ["users.id"],
            name=op.f("fk_orders_recipient_user_id_users"),
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_orders")),
    )
    op.execute(
        """
        CREATE UNIQUE INDEX uq_orders_one_open_per_author
        ON orders (author_id)
        WHERE status IN ('DRAFT', 'PENDING', 'ACTIVE')
        """
    )
    op.execute(
        """
        CREATE UNIQUE INDEX uq_orders_one_open_per_recipient
        ON orders (recipient_user_id)
        WHERE recipient_user_id IS NOT NULL AND status IN ('DRAFT', 'PENDING', 'ACTIVE')
        """
    )

    op.create_table(
        "invites",
        sa.Column("order_id", sa.UUID(), nullable=False),
        sa.Column("token", sa.String(length=64), nullable=False),
        sa.Column("status", invite_status, nullable=False),
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["order_id"],
            ["orders.id"],
            name=op.f("fk_invites_order_id_orders"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_invites")),
        sa.UniqueConstraint("order_id", name=op.f("uq_invites_order_id")),
        sa.UniqueConstraint("token", name=op.f("uq_invites_token")),
    )

    _repoint_to_order("user_qualities", "order_qualities", drop_unique=None)
    _repoint_to_order(
        "user_topics",
        "order_topics",
        drop_unique="uq_user_topics_user_topic",
        extra_unique=("order_id", "topic_id", "uq_order_topics_order_topic"),
    )
    _repoint_to_order("support_preferences", "support_preferences", drop_unique=None)
    _repoint_to_order("blocked_topics", "blocked_topics", drop_unique=None)
    _repoint_to_order("style_examples", "style_examples", drop_unique=None)

    op.add_column("schedules", sa.Column("order_id", sa.UUID(), nullable=True))
    op.create_foreign_key(
        op.f("fk_schedules_order_id_orders"),
        "schedules",
        "orders",
        ["order_id"],
        ["id"],
        ondelete="CASCADE",
    )
    op.create_unique_constraint(op.f("uq_schedules_order_id"), "schedules", ["order_id"])

    op.add_column("deliveries", sa.Column("order_id", sa.UUID(), nullable=True))
    op.create_foreign_key(
        op.f("fk_deliveries_order_id_orders"),
        "deliveries",
        "orders",
        ["order_id"],
        ["id"],
        ondelete="CASCADE",
    )

    op.add_column("generated_messages", sa.Column("order_id", sa.UUID(), nullable=True))
    op.create_foreign_key(
        op.f("fk_generated_messages_order_id_orders"),
        "generated_messages",
        "orders",
        ["order_id"],
        ["id"],
        ondelete="CASCADE",
    )


def _repoint_to_order(
    table: str,
    new_table: str,
    *,
    drop_unique: str | None,
    extra_unique: tuple[str, str, str] | None = None,
) -> None:
    op.add_column(table, sa.Column("order_id", sa.UUID(), nullable=True))
    op.drop_constraint(op.f(f"fk_{table}_user_id_users"), table, type_="foreignkey")
    if drop_unique is not None:
        op.drop_constraint(drop_unique, table, type_="unique")
    op.drop_column(table, "user_id")
    op.alter_column(table, "order_id", nullable=False)
    op.create_foreign_key(
        op.f(f"fk_{new_table}_order_id_orders"),
        table,
        "orders",
        ["order_id"],
        ["id"],
        ondelete="CASCADE",
    )
    if extra_unique is not None:
        col_a, col_b, name = extra_unique
        op.create_unique_constraint(name, table, [col_a, col_b])
    if table != new_table:
        op.rename_table(table, new_table)


def downgrade() -> None:
    op.drop_constraint(
        op.f("fk_generated_messages_order_id_orders"),
        "generated_messages",
        type_="foreignkey",
    )
    op.drop_column("generated_messages", "order_id")
    op.drop_constraint(op.f("fk_deliveries_order_id_orders"), "deliveries", type_="foreignkey")
    op.drop_column("deliveries", "order_id")
    op.drop_constraint(op.f("uq_schedules_order_id"), "schedules", type_="unique")
    op.drop_constraint(op.f("fk_schedules_order_id_orders"), "schedules", type_="foreignkey")
    op.drop_column("schedules", "order_id")

    _restore_user_fk(
        "order_topics",
        "user_topics",
        order_fk="fk_order_topics_order_id_orders",
        extra_unique="uq_order_topics_order_topic",
        restore_unique=("user_id", "topic_id", "uq_user_topics_user_topic"),
    )
    _restore_user_fk(
        "order_qualities", "user_qualities", order_fk="fk_order_qualities_order_id_orders"
    )
    _restore_user_fk(
        "support_preferences",
        "support_preferences",
        order_fk="fk_support_preferences_order_id_orders",
    )
    _restore_user_fk(
        "blocked_topics", "blocked_topics", order_fk="fk_blocked_topics_order_id_orders"
    )
    _restore_user_fk(
        "style_examples", "style_examples", order_fk="fk_style_examples_order_id_orders"
    )

    op.drop_table("invites")
    op.execute("DROP INDEX IF EXISTS uq_orders_one_open_per_recipient")
    op.execute("DROP INDEX IF EXISTS uq_orders_one_open_per_author")
    op.drop_table("orders")

    onboarding_step = sa.Enum(
        "CONSENT",
        "ADDRESS_MODE",
        "QUALITIES",
        "TOPICS",
        "SUPPORT_PREFERENCES",
        "BLOCKED_TOPICS",
        "STYLE_EXAMPLES",
        "TIMEZONE",
        "SCHEDULE_MODE",
        "SCHEDULE_TIME",
        "SUMMARY",
        "DONE",
        name="onboarding_step",
    )
    onboarding_step.create(op.get_bind(), checkfirst=True)
    op.add_column("users", sa.Column("onboarding_step", onboarding_step, nullable=True))
    op.add_column("users", sa.Column("address_mode", address_mode, nullable=True))
    op.drop_column("users", "recipient_step")
    op.drop_column("users", "author_step")
    op.drop_column("users", "role")
    op.drop_column("users", "telegram_username")

    invite_status.drop(op.get_bind(), checkfirst=True)
    order_status.drop(op.get_bind(), checkfirst=True)
    recipient_onboarding_step.drop(op.get_bind(), checkfirst=True)
    author_onboarding_step.drop(op.get_bind(), checkfirst=True)
    user_role.drop(op.get_bind(), checkfirst=True)


def _restore_user_fk(
    current: str,
    original: str,
    *,
    order_fk: str,
    extra_unique: str | None = None,
    restore_unique: tuple[str, str, str] | None = None,
) -> None:
    if extra_unique is not None:
        op.drop_constraint(extra_unique, current, type_="unique")
    op.drop_constraint(order_fk, current, type_="foreignkey")
    if current != original:
        op.rename_table(current, original)
        current = original
    op.add_column(current, sa.Column("user_id", sa.UUID(), nullable=False))
    op.drop_column(current, "order_id")
    op.create_foreign_key(
        op.f(f"fk_{current}_user_id_users"),
        current,
        "users",
        ["user_id"],
        ["id"],
        ondelete="CASCADE",
    )
    if restore_unique is not None:
        col_a, col_b, name = restore_unique
        op.create_unique_constraint(name, current, [col_a, col_b])
