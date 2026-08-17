"""split schedule onboarding step into mode and time

Revision ID: f5e93a177086
Revises: d247b06bc2b6
Create Date: 2026-08-17 09:38:22.372518

"""

from collections.abc import Sequence

from alembic import op

revision: str = "f5e93a177086"
down_revision: str | Sequence[str] | None = "d247b06bc2b6"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute("ALTER TYPE onboarding_step RENAME VALUE 'SCHEDULE' TO 'SCHEDULE_MODE'")
    op.execute(
        "ALTER TYPE onboarding_step ADD VALUE IF NOT EXISTS 'SCHEDULE_TIME' AFTER 'SCHEDULE_MODE'"
    )


def downgrade() -> None:
    op.execute("ALTER TYPE onboarding_step RENAME VALUE 'SCHEDULE_MODE' TO 'SCHEDULE'")
