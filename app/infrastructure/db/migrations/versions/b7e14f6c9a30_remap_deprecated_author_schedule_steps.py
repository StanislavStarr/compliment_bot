"""remap leftover author schedule steps after monolith removal

Revision ID: b7e14f6c9a30
Revises: e4b91c7a2d08
Create Date: 2026-09-14 21:10:00.000000

"""

from collections.abc import Sequence

from alembic import op

revision: str = "b7e14f6c9a30"
down_revision: str | Sequence[str] | None = "e4b91c7a2d08"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute(
        """
        UPDATE users
        SET author_step = 'CONSENT'
        WHERE author_step IN ('TIMEZONE', 'SCHEDULE_MODE', 'SCHEDULE_TIME')
        """
    )


def downgrade() -> None:
    pass
