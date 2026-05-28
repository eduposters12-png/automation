import enum
import uuid
from datetime import date, datetime
from typing import Any

from sqlalchemy import Boolean, Date, DateTime, Enum, ForeignKey, Integer, Text, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from backend.app.db.base import Base


class AutoMode(str, enum.Enum):
    MANUAL = "MANUAL"
    AUTO = "AUTO"
    HYBRID = "HYBRID"


class QualityMode(str, enum.Enum):
    FULL = "FULL"
    BALANCED = "BALANCED"
    FAST = "FAST"


class AutoLogEvent(str, enum.Enum):
    LISTING_CREATED = "LISTING_CREATED"
    TOPIC_EXHAUSTED = "TOPIC_EXHAUSTED"
    CREDITS_LOW = "CREDITS_LOW"
    CREDITS_EXHAUSTED = "CREDITS_EXHAUSTED"
    QUALITY_ADJUSTED = "QUALITY_ADJUSTED"
    DAILY_LIMIT_REACHED = "DAILY_LIMIT_REACHED"
    AUTO_PAUSED = "AUTO_PAUSED"
    AUTO_RESUMED = "AUTO_RESUMED"
    TOPIC_AUTO_DISCOVERED = "TOPIC_AUTO_DISCOVERED"
    ERROR = "ERROR"


class AutomationConfig(Base):
    __tablename__ = "automation_configs"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    shop_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("shops.id", ondelete="CASCADE"),
        unique=True,
        nullable=False
    )
    mode: Mapped[AutoMode] = mapped_column(Enum(AutoMode, name="auto_mode"), default=AutoMode.MANUAL, nullable=False)
    topics_json: Mapped[list[dict[str, Any]]] = mapped_column(JSONB, default=list, nullable=False)
    daily_limit: Mapped[int] = mapped_column(Integer, default=10, nullable=False)
    target_min_listings: Mapped[int | None] = mapped_column(Integer)
    target_max_listings: Mapped[int | None] = mapped_column(Integer)
    quality_mode: Mapped[QualityMode] = mapped_column(
        Enum(QualityMode, name="quality_mode"),
        default=QualityMode.FULL,
        nullable=False
    )
    auto_quality_adjust: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    is_running: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    last_run_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    listings_created_today: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    listings_created_total: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    today_date: Mapped[date | None] = mapped_column(Date)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), onupdate=func.now())


class AutomationLog(Base):
    __tablename__ = "automation_logs"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    shop_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("shops.id", ondelete="CASCADE"),
        index=True,
        nullable=False
    )
    event_type: Mapped[AutoLogEvent] = mapped_column(
        Enum(AutoLogEvent, name="auto_log_event"),
        nullable=False
    )
    message: Mapped[str] = mapped_column(Text, nullable=False)
    metadata_json: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
