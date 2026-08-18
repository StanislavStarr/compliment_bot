"""add total_tokens to generated_messages

Revision ID: a1c7e3f9b2d4
Revises: f5e93a177086
Create Date: 2026-08-17 09:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "a1c7e3f9b2d4"
down_revision: str | Sequence[str] | None = "f5e93a177086"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("generated_messages", sa.Column("total_tokens", sa.Integer(), nullable=True))


def downgrade() -> None:
    op.drop_column("generated_messages", "total_tokens")
