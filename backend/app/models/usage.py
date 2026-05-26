import enum
import uuid
from datetime import datetime

from sqlalchemy import DateTime, Enum, ForeignKey, Integer, String, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from backend.app.db.base import Base


class UsageAction(str, enum.Enum):
    IMAGE_GENERATED = "IMAGE_GENERATED"
    VIDEO_GENERATED = "VIDEO_GENERATED"
    LISTING_UPLOADED = "LISTING_UPLOADED"


class Usage(Base):
    __tablename__ = "usage"
    __table_args__ = (
        UniqueConstraint("user_id", "action", "month", name="uq_usage_user_action_month"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), index=True)
    action: Mapped[UsageAction] = mapped_column(Enum(UsageAction, name="usage_action"), nullable=False)
    count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    month: Mapped[str] = mapped_column(String(7), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
