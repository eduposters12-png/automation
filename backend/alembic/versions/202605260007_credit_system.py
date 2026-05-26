"""add credit system

Revision ID: 202605260007
Revises: 202605250006
Create Date: 2026-05-26
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "202605260007"
down_revision: Union[str, None] = "202605250006"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

credit_action_enum = sa.Enum(
    "IMAGE_GENERATION",
    "IMAGE_REGENERATION",
    "HIGH_RES_IMAGE",
    "VIDEO_GENERATION",
    "COPY_GENERATION",
    "ETSY_LISTING_UPLOAD",
    "MONTHLY_PLAN_GRANT",
    "SIGNUP_GRANT",
    "MANUAL_ADJUSTMENT",
    "REFUND",
    name="credit_action"
)


def upgrade() -> None:
    credit_action_enum.create(op.get_bind(), checkfirst=True)
    op.add_column("users", sa.Column("credit_balance", sa.Integer(), server_default="0", nullable=False))
    op.create_table(
        "credit_ledger",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("action", credit_action_enum, nullable=False),
        sa.Column("credits_delta", sa.Integer(), nullable=False),
        sa.Column("balance_after", sa.Integer(), nullable=False),
        sa.Column("listing_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("job_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("idempotency_key", sa.String(length=255), nullable=True),
        sa.Column("metadata_json", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["job_id"], ["jobs.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["listing_id"], ["listings.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id")
    )
    op.create_index("ix_credit_ledger_user_id", "credit_ledger", ["user_id"])
    op.create_index("ix_credit_ledger_listing_id", "credit_ledger", ["listing_id"])
    op.create_index("ix_credit_ledger_job_id", "credit_ledger", ["job_id"])
    op.create_index("ix_credit_ledger_idempotency_key", "credit_ledger", ["idempotency_key"], unique=True)


def downgrade() -> None:
    op.drop_index("ix_credit_ledger_idempotency_key", table_name="credit_ledger")
    op.drop_index("ix_credit_ledger_job_id", table_name="credit_ledger")
    op.drop_index("ix_credit_ledger_listing_id", table_name="credit_ledger")
    op.drop_index("ix_credit_ledger_user_id", table_name="credit_ledger")
    op.drop_table("credit_ledger")
    op.drop_column("users", "credit_balance")
    credit_action_enum.drop(op.get_bind(), checkfirst=True)
