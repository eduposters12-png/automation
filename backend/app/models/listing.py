import enum
import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import Boolean, DateTime, Enum, ForeignKey, Integer, Numeric, String, Text, func, text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.app.db.base import Base


class ListingStatus(str, enum.Enum):
    DRAFT = "DRAFT"
    QUEUED = "QUEUED"
    QUEUED_MANUAL = "QUEUED_MANUAL"
    IMAGE_APPROVED = "IMAGE_APPROVED"
    COPY_READY = "COPY_READY"
    READY_TO_UPLOAD = "READY_TO_UPLOAD"
    LIVE = "LIVE"
    FAILED = "FAILED"


class Listing(Base):
    __tablename__ = "listings"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    shop_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("shops.id", ondelete="CASCADE"),
        index=True,
        nullable=False
    )
    status: Mapped[ListingStatus] = mapped_column(
        Enum(ListingStatus, name="listing_status"),
        default=ListingStatus.DRAFT,
        nullable=False
    )
    image_urls: Mapped[list[str]] = mapped_column(JSONB, default=list, nullable=False)
    image_prompt: Mapped[str | None] = mapped_column(Text)
    claude_review_json: Mapped[dict | None] = mapped_column(JSONB)
    primary_image_url: Mapped[str | None] = mapped_column(String(1000))
    video_url: Mapped[str | None] = mapped_column(String(1000))
    title: Mapped[str | None] = mapped_column(String(140))
    description: Mapped[str | None] = mapped_column(Text)
    tags: Mapped[list[str]] = mapped_column(JSONB, default=list, nullable=False)
    price: Mapped[Decimal | None] = mapped_column(Numeric(10, 2))
    is_bundle: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_multi_page: Mapped[bool] = mapped_column(Boolean, default=False, server_default="false", nullable=False)
    page_plan_json: Mapped[dict | None] = mapped_column(JSONB)
    page_images_json: Mapped[list[dict]] = mapped_column(
        JSONB,
        default=list,
        server_default=text("'[]'"),
        nullable=False
    )
    pdf_url: Mapped[str | None] = mapped_column(String(1000))
    total_pages_planned: Mapped[int | None] = mapped_column(Integer)
    pages_completed: Mapped[int] = mapped_column(Integer, default=0, server_default="0", nullable=False)
    etsy_listing_id: Mapped[str | None] = mapped_column(String(255), index=True)
    error_message: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    shop = relationship("Shop", back_populates="listings")
