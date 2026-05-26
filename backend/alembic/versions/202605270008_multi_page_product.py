"""add multi page digital product fields

Revision ID: 202605270008
Revises: 202605260007
Create Date: 2026-05-27
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "202605270008"
down_revision: Union[str, None] = "202605260007"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _has_column(table_name: str, column_name: str) -> bool:
    bind = op.get_bind()
    columns = sa.inspect(bind).get_columns(table_name)
    return any(column["name"] == column_name for column in columns)


def _add_column_if_missing(table_name: str, column: sa.Column) -> None:
    if not _has_column(table_name, column.name):
        op.add_column(table_name, column)


def upgrade() -> None:
    _add_column_if_missing(
        "listings",
        sa.Column("is_multi_page", sa.Boolean(), server_default=sa.text("false"), nullable=False)
    )
    _add_column_if_missing(
        "listings",
        sa.Column("page_plan_json", postgresql.JSONB(astext_type=sa.Text()), nullable=True)
    )
    _add_column_if_missing(
        "listings",
        sa.Column(
            "page_images_json",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'[]'"),
            nullable=False
        )
    )
    _add_column_if_missing("listings", sa.Column("pdf_url", sa.String(length=1000), nullable=True))
    _add_column_if_missing("listings", sa.Column("total_pages_planned", sa.Integer(), nullable=True))
    _add_column_if_missing(
        "listings",
        sa.Column("pages_completed", sa.Integer(), server_default=sa.text("0"), nullable=False)
    )


def downgrade() -> None:
    op.drop_column("listings", "pages_completed")
    op.drop_column("listings", "total_pages_planned")
    op.drop_column("listings", "pdf_url")
    op.drop_column("listings", "page_images_json")
    op.drop_column("listings", "page_plan_json")
    op.drop_column("listings", "is_multi_page")
