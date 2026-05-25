"""initial schema

Revision ID: 202605250001
Revises:
Create Date: 2026-05-25
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "202605250001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


plan_enum = sa.Enum("FREE", "BASIC", "PRO", "AGENCY", name="plan")
listing_status_enum = sa.Enum("DRAFT", "QUEUED", "LIVE", "FAILED", name="listing_status")
job_type_enum = sa.Enum("ANALYZE", "GENERATE_IMAGE", "GENERATE_VIDEO", "UPLOAD_LISTING", name="job_type")
job_status_enum = sa.Enum("PENDING", "RUNNING", "DONE", "FAILED", name="job_status")


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("email", sa.String(length=255), nullable=False),
        sa.Column("name", sa.String(length=160), nullable=False),
        sa.Column("password_hash", sa.String(length=255), nullable=False),
        sa.Column("plan", plan_enum, nullable=False),
        sa.Column("stripe_customer_id", sa.String(length=255), nullable=True),
        sa.Column("stripe_subscription_id", sa.String(length=255), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("email"),
        sa.UniqueConstraint("stripe_customer_id"),
        sa.UniqueConstraint("stripe_subscription_id")
    )
    op.create_index("ix_users_email", "users", ["email"])

    op.create_table(
        "shops",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("shop_url", sa.String(length=500), nullable=True),
        sa.Column("shop_name", sa.String(length=255), nullable=True),
        sa.Column("niche", sa.String(length=255), nullable=True),
        sa.Column("etsy_access_token_encrypted", sa.Text(), nullable=True),
        sa.Column("etsy_refresh_token_encrypted", sa.Text(), nullable=True),
        sa.Column("etsy_token_expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("claude_api_key_encrypted", sa.Text(), nullable=True),
        sa.Column("analysis_json", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("last_analyzed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id")
    )
    op.create_index("ix_shops_user_id", "shops", ["user_id"])

    op.create_table(
        "listings",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("shop_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("status", listing_status_enum, nullable=False),
        sa.Column("image_urls", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("video_url", sa.String(length=1000), nullable=True),
        sa.Column("title", sa.String(length=140), nullable=True),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("tags", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("price", sa.Numeric(10, 2), nullable=True),
        sa.Column("etsy_listing_id", sa.String(length=255), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["shop_id"], ["shops.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id")
    )
    op.create_index("ix_listings_shop_id", "listings", ["shop_id"])
    op.create_index("ix_listings_etsy_listing_id", "listings", ["etsy_listing_id"])

    op.create_table(
        "jobs",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("shop_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("type", job_type_enum, nullable=False),
        sa.Column("status", job_status_enum, nullable=False),
        sa.Column("payload_json", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("result_json", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["shop_id"], ["shops.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id")
    )
    op.create_index("ix_jobs_shop_id", "jobs", ["shop_id"])


def downgrade() -> None:
    op.drop_index("ix_jobs_shop_id", table_name="jobs")
    op.drop_table("jobs")
    op.drop_index("ix_listings_etsy_listing_id", table_name="listings")
    op.drop_index("ix_listings_shop_id", table_name="listings")
    op.drop_table("listings")
    op.drop_index("ix_shops_user_id", table_name="shops")
    op.drop_table("shops")
    op.drop_index("ix_users_email", table_name="users")
    op.drop_table("users")
    job_status_enum.drop(op.get_bind(), checkfirst=True)
    job_type_enum.drop(op.get_bind(), checkfirst=True)
    listing_status_enum.drop(op.get_bind(), checkfirst=True)
    plan_enum.drop(op.get_bind(), checkfirst=True)
