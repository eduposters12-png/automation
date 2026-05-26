import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.app.db.base import Base


class Shop(Base):
    __tablename__ = "shops"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        index=True,
        nullable=False
    )
    shop_url: Mapped[str | None] = mapped_column(String(500))
    shop_name: Mapped[str | None] = mapped_column(String(255))
    etsy_shop_id: Mapped[str | None] = mapped_column(String(255), index=True)
    niche: Mapped[str | None] = mapped_column(String(255))
    etsy_access_token_encrypted: Mapped[str | None] = mapped_column(Text)
    etsy_refresh_token_encrypted: Mapped[str | None] = mapped_column(Text)
    etsy_token_expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    claude_api_key_encrypted: Mapped[str | None] = mapped_column(Text)
    analysis_json: Mapped[dict | None] = mapped_column(JSONB)
    last_analyzed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    user = relationship("User", back_populates="shops")
    listings = relationship("Listing", back_populates="shop", cascade="all, delete-orphan")
    jobs = relationship("Job", back_populates="shop", cascade="all, delete-orphan")
