"""add etsy upload queue fields

Revision ID: 202605250005
Revises: 202605250004
Create Date: 2026-05-25
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "202605250005"
down_revision: Union[str, None] = "202605250004"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("ALTER TYPE listing_status ADD VALUE IF NOT EXISTS 'QUEUED'")
    op.execute("ALTER TYPE listing_status ADD VALUE IF NOT EXISTS 'QUEUED_MANUAL'")
    op.execute("ALTER TYPE listing_status ADD VALUE IF NOT EXISTS 'LIVE'")
    op.execute("ALTER TYPE listing_status ADD VALUE IF NOT EXISTS 'FAILED'")
    op.add_column("shops", sa.Column("etsy_shop_id", sa.String(length=255), nullable=True))
    op.create_index("ix_shops_etsy_shop_id", "shops", ["etsy_shop_id"])
    op.add_column("listings", sa.Column("error_message", sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column("listings", "error_message")
    op.drop_index("ix_shops_etsy_shop_id", table_name="shops")
    op.drop_column("shops", "etsy_shop_id")
