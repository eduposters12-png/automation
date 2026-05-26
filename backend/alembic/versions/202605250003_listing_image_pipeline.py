"""add listing image pipeline fields

Revision ID: 202605250003
Revises: 202605250002
Create Date: 2026-05-25
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "202605250003"
down_revision: Union[str, None] = "202605250002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("ALTER TYPE listing_status ADD VALUE IF NOT EXISTS 'IMAGE_APPROVED'")
    op.add_column("listings", sa.Column("image_prompt", sa.Text(), nullable=True))
    op.add_column("listings", sa.Column("claude_review_json", postgresql.JSONB(astext_type=sa.Text()), nullable=True))
    op.add_column("listings", sa.Column("primary_image_url", sa.String(length=1000), nullable=True))


def downgrade() -> None:
    op.drop_column("listings", "primary_image_url")
    op.drop_column("listings", "claude_review_json")
    op.drop_column("listings", "image_prompt")
