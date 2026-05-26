from decimal import Decimal
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field


class GenerateImageRequest(BaseModel):
    product_idea_index: int = Field(ge=0)
    is_high_res: bool = False
    product_title: str | None = Field(default=None, max_length=140)
    keywords: list[str] = Field(default_factory=list, max_length=13)
    style_notes: str | None = Field(default=None, max_length=600)
    estimated_price: Decimal | None = Field(default=None, ge=0)
    listing_id: UUID | None = None


class RegenerateImageRequest(BaseModel):
    use_improved_prompt: bool = False


class ApproveImageRequest(BaseModel):
    approved_image_url: str = Field(min_length=1, max_length=1200)


class ListingCopyUpdateRequest(BaseModel):
    title: str | None = Field(default=None, max_length=140)
    description: str | None = None
    tags: list[str] | None = Field(default=None, max_length=13)
    price: Decimal | None = Field(default=None, ge=0)


class BundleRequest(BaseModel):
    is_bundle: bool


class ListingUploadRequest(BaseModel):
    mode: Literal["auto", "manual"]
    disclaimer_accepted: bool = False


class BulkQueueRequest(BaseModel):
    listing_ids: list[UUID] = Field(min_length=1)
    disclaimer_accepted: bool = False


class ImageGenerationResponse(BaseModel):
    listing_id: UUID
    image_url: str
    claude_review: dict
    image_urls: list[str]
    review_unavailable: bool = False


class RegenerateImageResponse(BaseModel):
    image_url: str
    claude_review: dict
    image_urls: list[str]
    review_unavailable: bool = False


class HighResImageResponse(BaseModel):
    image_url: str
    image_urls: list[str]


class ListingImagesResponse(BaseModel):
    image_urls: list[str]
    current_image_url: str | None
    claude_review: dict | None
    image_prompt: str | None


class ApproveImageResponse(BaseModel):
    success: bool


class GenerateVideoResponse(BaseModel):
    video_url: str


class GenerateCopyResponse(BaseModel):
    title: str
    description: str
    tags: list[str]
    suggestedPrice: float


class ListingPackageResponse(BaseModel):
    listing_id: UUID
    image_urls: list[str]
    primary_image_url: str | None
    video_url: str | None
    title: str | None
    description: str | None
    tags: list[str]
    price: float | None
    status: str
    is_bundle: bool


class SuccessResponse(BaseModel):
    success: bool


class ListingUploadResponse(BaseModel):
    success: bool = True
    message: str
    job_id: str | None = None


class ListingStatusResponse(BaseModel):
    status: str
    etsy_listing_id: str | None
    etsy_listing_url: str | None
    error_message: str | None


class PaginatedListingsResponse(BaseModel):
    listings: list[dict]
    total: int
    page: int
    per_page: int


class BulkQueueResponse(BaseModel):
    queued_count: int
