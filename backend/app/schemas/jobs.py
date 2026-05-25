from datetime import datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from backend.app.models.job import JobStatus, JobType
from backend.app.models.listing import ListingStatus


class AnalyzeShopRequest(BaseModel):
    focus: str | None = Field(default=None, max_length=300)


class GenerateListingRequest(BaseModel):
    product_idea: str = Field(min_length=3, max_length=300)
    target_price: Decimal | None = Field(default=None, ge=0)


class UploadListingRequest(BaseModel):
    listing_id: UUID


class JobOut(BaseModel):
    id: UUID
    type: JobType
    status: JobStatus
    payload_json: dict
    result_json: dict | None
    error_message: str | None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ListingOut(BaseModel):
    id: UUID
    status: ListingStatus
    image_urls: list[str]
    video_url: str | None
    title: str | None
    description: str | None
    tags: list[str]
    price: Decimal | None
    etsy_listing_id: str | None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
