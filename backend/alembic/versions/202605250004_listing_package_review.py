"""add listing package review fields

Revision ID: 202605250004
Revises: 202605250003
Create Date: 2026-05-25
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "202605250004"
down_revision: Union[str, None] = "202605250003"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("ALTER TYPE listing_status ADD VALUE IF NOT EXISTS 'COPY_READY'")
    op.execute("ALTER TYPE listing_status ADD VALUE IF NOT EXISTS 'READY_TO_UPLOAD'")
    op.add_column(
        "listings",
        sa.Column("is_bundle", sa.Boolean(), server_default=sa.false(), nullable=False)
    )


def downgrade() -> None:
    op.drop_column("listings", "is_bundle")
