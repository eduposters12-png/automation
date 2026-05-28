import enum
import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import Boolean, DateTime, Enum, ForeignKey, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from backend.app.db.base import Base


class NotificationType(str, enum.Enum):
    CREDITS_LOW = "CREDITS_LOW"
    CREDITS_EXHAUSTED = "CREDITS_EXHAUSTED"
    QUALITY_ADJUSTED = "QUALITY_ADJUSTED"
    DAILY_LIMIT_REACHED = "DAILY_LIMIT_REACHED"
    AUTO_PAUSED = "AUTO_PAUSED"
    LISTING_CREATED = "LISTING_CREATED"
    TOPIC_EXHAUSTED = "TOPIC_EXHAUSTED"
    AUTO_TOPIC_DISCOVERED = "AUTO_TOPIC_DISCOVERED"


class Notification(Base):
    __tablename__ = "notifications"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        index=True,
        nullable=False
    )
    type: Mapped[NotificationType] = mapped_column(
        Enum(NotificationType, name="notification_type"),
        nullable=False
    )
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    is_read: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False, index=True)
    action_url: Mapped[str | None] = mapped_column(String(500))
    metadata_json: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
