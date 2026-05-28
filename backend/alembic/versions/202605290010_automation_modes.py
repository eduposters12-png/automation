"""add automation modes

Revision ID: 202605290010
Revises: 202605280009
Create Date: 2026-05-29
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "202605290010"
down_revision: Union[str, None] = "202605280009"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

auto_mode_enum = sa.Enum("MANUAL", "AUTO", "HYBRID", name="auto_mode")
quality_mode_enum = sa.Enum("FULL", "BALANCED", "FAST", name="quality_mode")
auto_log_event_enum = sa.Enum(
    "LISTING_CREATED",
    "TOPIC_EXHAUSTED",
    "CREDITS_LOW",
    "CREDITS_EXHAUSTED",
    "QUALITY_ADJUSTED",
    "DAILY_LIMIT_REACHED",
    "AUTO_PAUSED",
    "AUTO_RESUMED",
    "TOPIC_AUTO_DISCOVERED",
    "ERROR",
    name="auto_log_event"
)
notification_type_enum = sa.Enum(
    "CREDITS_LOW",
    "CREDITS_EXHAUSTED",
    "QUALITY_ADJUSTED",
    "DAILY_LIMIT_REACHED",
    "AUTO_PAUSED",
    "LISTING_CREATED",
    "TOPIC_EXHAUSTED",
    "AUTO_TOPIC_DISCOVERED",
    name="notification_type"
)


def upgrade() -> None:
    auto_mode_enum.create(op.get_bind(), checkfirst=True)
    quality_mode_enum.create(op.get_bind(), checkfirst=True)
    auto_log_event_enum.create(op.get_bind(), checkfirst=True)
    notification_type_enum.create(op.get_bind(), checkfirst=True)

    op.create_table(
        "automation_configs",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("shop_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("mode", auto_mode_enum, nullable=False),
        sa.Column("topics_json", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("daily_limit", sa.Integer(), nullable=False),
        sa.Column("target_min_listings", sa.Integer(), nullable=True),
        sa.Column("target_max_listings", sa.Integer(), nullable=True),
        sa.Column("quality_mode", quality_mode_enum, nullable=False),
        sa.Column("auto_quality_adjust", sa.Boolean(), nullable=False),
        sa.Column("is_running", sa.Boolean(), nullable=False),
        sa.Column("last_run_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("listings_created_today", sa.Integer(), nullable=False),
        sa.Column("listings_created_total", sa.Integer(), nullable=False),
        sa.Column("today_date", sa.Date(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["shop_id"], ["shops.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("shop_id")
    )

    op.create_table(
        "automation_logs",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("shop_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("event_type", auto_log_event_enum, nullable=False),
        sa.Column("message", sa.Text(), nullable=False),
        sa.Column("metadata_json", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["shop_id"], ["shops.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id")
    )
    op.create_index("ix_automation_logs_shop_id", "automation_logs", ["shop_id"])

    op.create_table(
        "notifications",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("type", notification_type_enum, nullable=False),
        sa.Column("title", sa.String(length=200), nullable=False),
        sa.Column("message", sa.Text(), nullable=False),
        sa.Column("is_read", sa.Boolean(), nullable=False),
        sa.Column("action_url", sa.String(length=500), nullable=True),
        sa.Column("metadata_json", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id")
    )
    op.create_index("ix_notifications_user_id", "notifications", ["user_id"])
    op.create_index("ix_notifications_is_read", "notifications", ["is_read"])


def downgrade() -> None:
    op.drop_index("ix_notifications_is_read", table_name="notifications")
    op.drop_index("ix_notifications_user_id", table_name="notifications")
    op.drop_table("notifications")
    op.drop_index("ix_automation_logs_shop_id", table_name="automation_logs")
    op.drop_table("automation_logs")
    op.drop_table("automation_configs")
    notification_type_enum.drop(op.get_bind(), checkfirst=True)
    auto_log_event_enum.drop(op.get_bind(), checkfirst=True)
    quality_mode_enum.drop(op.get_bind(), checkfirst=True)
    auto_mode_enum.drop(op.get_bind(), checkfirst=True)
