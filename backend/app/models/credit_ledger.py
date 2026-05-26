import enum
import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import DateTime, Enum, ForeignKey, Integer, String, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from backend.app.db.base import Base


class CreditAction(str, enum.Enum):
    IMAGE_GENERATION = "IMAGE_GENERATION"
    IMAGE_REGENERATION = "IMAGE_REGENERATION"
    HIGH_RES_IMAGE = "HIGH_RES_IMAGE"
    VIDEO_GENERATION = "VIDEO_GENERATION"
    COPY_GENERATION = "COPY_GENERATION"
    ETSY_LISTING_UPLOAD = "ETSY_LISTING_UPLOAD"
    MONTHLY_PLAN_GRANT = "MONTHLY_PLAN_GRANT"
    SIGNUP_GRANT = "SIGNUP_GRANT"
    MANUAL_ADJUSTMENT = "MANUAL_ADJUSTMENT"
    REFUND = "REFUND"


class CreditLedger(Base):
    __tablename__ = "credit_ledger"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        index=True,
        nullable=False
    )
    action: Mapped[CreditAction] = mapped_column(Enum(CreditAction, name="credit_action"), nullable=False)
    credits_delta: Mapped[int] = mapped_column(Integer, nullable=False)
    balance_after: Mapped[int] = mapped_column(Integer, nullable=False)
    listing_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("listings.id", ondelete="SET NULL"),
        index=True
    )
    job_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("jobs.id", ondelete="SET NULL"),
        index=True
    )
    idempotency_key: Mapped[str | None] = mapped_column(String(255), unique=True)
    metadata_json: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
