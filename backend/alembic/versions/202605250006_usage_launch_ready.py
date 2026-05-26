"""add usage tracking and soft delete

Revision ID: 202605250006
Revises: 202605250005
Create Date: 2026-05-25
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "202605250006"
down_revision: Union[str, None] = "202605250005"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

usage_action_enum = sa.Enum("IMAGE_GENERATED", "VIDEO_GENERATED", "LISTING_UPLOADED", name="usage_action")


def upgrade() -> None:
    usage_action_enum.create(op.get_bind(), checkfirst=True)
    op.add_column("users", sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True))
    op.create_table(
        "usage",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("action", usage_action_enum, nullable=False),
        sa.Column("count", sa.Integer(), nullable=False),
        sa.Column("month", sa.String(length=7), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", "action", "month", name="uq_usage_user_action_month")
    )
    op.create_index("ix_usage_user_id", "usage", ["user_id"])


def downgrade() -> None:
    op.drop_index("ix_usage_user_id", table_name="usage")
    op.drop_table("usage")
    op.drop_column("users", "deleted_at")
    usage_action_enum.drop(op.get_bind(), checkfirst=True)
