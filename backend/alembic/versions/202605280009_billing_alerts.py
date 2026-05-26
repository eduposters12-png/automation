"""add billing alert credit cycle fields

Revision ID: 202605280009
Revises: 202605270008
Create Date: 2026-05-28
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "202605280009"
down_revision: Union[str, None] = "202605270008"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("users", sa.Column("credit_cycle_start", sa.DateTime(timezone=True), nullable=True))
    op.add_column("users", sa.Column("credit_cycle_end", sa.DateTime(timezone=True), nullable=True))
    op.add_column("users", sa.Column("last_credit_reset", sa.DateTime(timezone=True), nullable=True))


def downgrade() -> None:
    op.drop_column("users", "last_credit_reset")
    op.drop_column("users", "credit_cycle_end")
    op.drop_column("users", "credit_cycle_start")
