from io import BytesIO
from decimal import Decimal, InvalidOperation
from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import StreamingResponse
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from backend.app.core.deps import get_current_user
from backend.app.core.security import decrypt_secret
from backend.app.db.session import get_db
from backend.app.models.listing import Listing, ListingStatus
from backend.app.models.shop import Shop
from backend.app.models.user import Plan, User
from backend.app.schemas.listings import (
    ApproveImageRequest,
    ApproveImageResponse,
    BulkQueueRequest,
    BulkQueueResponse,
    BundleRequest,
    GenerateCopyResponse,
    GenerateImageRequest,
    GenerateVideoResponse,
    HighResImageResponse,
    ImageGenerationResponse,
    ListingStatusResponse,
    ListingCopyUpdateRequest,
    ListingImagesResponse,
    ListingPackageResponse,
    ListingUploadRequest,
    ListingUploadResponse,
    PaginatedListingsResponse,
    RegenerateImageRequest,
    RegenerateImageResponse,
    SuccessResponse
)
from backend.app.services.copy_service import CopyGenerationError, CopyJSONParseError, generate_listing_copy
from backend.app.services.image_review_service import choose_image_prompt_and_size, review_image
from backend.app.services.image_service import (
    CloudinaryUploadError,
    ImageGenerationError,
    build_image_prompt,
    generate_product_image,
    upload_to_cloudinary
)
from backend.app.services.etsy_upload_service import listing_to_upload_dict
from backend.app.services.queue_service import enqueue_upload_job
from backend.app.services.shops import get_primary_shop
from backend.app.services.video_service import (
    VideoGenerationError,
    VideoUploadError,
    generate_listing_video,
    upload_video
)
from backend.app.services.zip_service import ZipCreationError, create_listing_zip

router = APIRouter(prefix="/listings", tags=["listings"])

IMAGE_LIMITS: dict[Plan, int | None] = {
    Plan.FREE: 0,
    Plan.BASIC: 3,
    Plan.PRO: 10,
    Plan.AGENCY: None
}


def _require_shop(current_user: User, db: Session) -> Shop:
    shop = get_primary_shop(db, current_user)
    if not shop:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Connect your Etsy shop first")
    return shop


def _require_claude_key(shop: Shop) -> str:
    if not shop.claude_api_key_encrypted:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Add your Claude API key first")
    return decrypt_secret(shop.claude_api_key_encrypted)


def _owned_listing(db: Session, shop: Shop, listing_id: UUID) -> Listing:
    listing = db.get(Listing, listing_id)
    if not listing or listing.shop_id != shop.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Listing not found")
    return listing


def _image_limit(plan: Plan) -> int | None:
    return IMAGE_LIMITS[plan]


def _require_image_generation_allowed(current_user: User, listing: Listing | None, is_high_res: bool) -> None:
    if current_user.plan == Plan.FREE:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Upgrade your plan to generate images."
        )
    if is_high_res and current_user.plan not in {Plan.PRO, Plan.AGENCY}:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="High resolution requires Pro plan."
        )

    limit = _image_limit(current_user.plan)
    if listing and limit is not None and len(listing.image_urls or []) >= limit:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Image limit reached for your plan."
        )


def _require_video_generation_allowed(current_user: User) -> None:
    if current_user.plan not in {Plan.PRO, Plan.AGENCY}:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Video generation requires Pro plan."
        )


def _require_etsy_connection(shop: Shop) -> None:
    if not shop.etsy_access_token_encrypted:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Please reconnect your Etsy shop in Settings."
        )


def _require_upload_ready(listing: Listing) -> None:
    if not listing.title or not listing.description or not (listing.image_urls or []):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Listing package is incomplete.")


def _product_ideas(shop: Shop) -> list[dict[str, Any]]:
    analysis = shop.analysis_json or {}
    ideas = analysis.get("productIdeas") if isinstance(analysis, dict) else None
    if not isinstance(ideas, list):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Run shop analysis before generating images."
        )
    return [idea for idea in ideas if isinstance(idea, dict)]


def _product_idea_from_analysis(shop: Shop, index: int) -> dict[str, Any]:
    ideas = _product_ideas(shop)
    if index >= len(ideas):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Product idea not found.")
    return dict(ideas[index])


def _apply_product_overrides(product_idea: dict[str, Any], payload: GenerateImageRequest) -> dict[str, Any]:
    product = dict(product_idea)
    if payload.product_title:
        product["title"] = payload.product_title.strip()
    if payload.keywords:
        product["targetKeywords"] = [keyword.strip() for keyword in payload.keywords if keyword.strip()]
    if payload.estimated_price is not None:
        product["suggestedPrice"] = float(payload.estimated_price)
    return product


def _target_keywords(product_idea: dict[str, Any]) -> list[str]:
    keywords = product_idea.get("targetKeywords") or product_idea.get("keywords") or []
    if not isinstance(keywords, list):
        return []
    return [str(keyword) for keyword in keywords if keyword][:13]


def _suggested_price(product_idea: dict[str, Any]) -> Decimal | None:
    value = product_idea.get("suggestedPrice")
    if value is None:
        return None
    try:
        return Decimal(str(value))
    except (InvalidOperation, TypeError, ValueError):
        return None


def _shop_style(shop: Shop, style_notes: str | None) -> str:
    analysis = shop.analysis_json or {}
    style = analysis.get("style") if isinstance(analysis, dict) else None
    parts = [str(style or shop.niche or "clean Etsy product style")]
    if style_notes and style_notes.strip():
        parts.append(f"Seller notes: {style_notes.strip()}")
    return ". ".join(parts)


def _shop_analysis(shop: Shop) -> dict[str, Any]:
    return shop.analysis_json if isinstance(shop.analysis_json, dict) else {}


def _listing_product_idea(shop: Shop, listing: Listing) -> dict[str, Any]:
    title = listing.title or "Etsy product"
    product_idea: dict[str, Any] = {
        "title": title,
        "targetKeywords": listing.tags or [],
        "suggestedPrice": float(listing.price) if listing.price is not None else None
    }
    analysis = _shop_analysis(shop)
    ideas = analysis.get("productIdeas")
    if isinstance(ideas, list):
        matching_idea = next(
            (
                idea
                for idea in ideas
                if isinstance(idea, dict)
                and str(idea.get("title") or "").strip().lower() == title.strip().lower()
            ),
            None
        )
        if matching_idea:
            product_idea = {**matching_idea, **product_idea}
    return product_idea


def _video_image_urls(listing: Listing) -> list[str]:
    if not listing.primary_image_url:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No approved images found for this listing."
        )
    ordered_urls = [listing.primary_image_url]
    ordered_urls.extend(url for url in (listing.image_urls or []) if url != listing.primary_image_url)
    return ordered_urls


def _copy_price(value: Any) -> Decimal | None:
    if value is None:
        return None
    try:
        return Decimal(str(value))
    except (InvalidOperation, ValueError):
        return None


def _price_as_float(value: Decimal | None) -> float | None:
    return float(value) if value is not None else None


def _clean_tags(tags: list[str]) -> list[str]:
    cleaned: list[str] = []
    for tag in tags:
        value = str(tag).strip()
        if value and value not in cleaned:
            cleaned.append(value)
    return cleaned[:13]


def _listing_out_dict(listing: Listing) -> dict[str, Any]:
    return {
        "id": str(listing.id),
        "status": listing.status.value,
        "image_urls": list(listing.image_urls or []),
        "primary_image_url": listing.primary_image_url,
        "image_prompt": listing.image_prompt,
        "claude_review_json": listing.claude_review_json,
        "video_url": listing.video_url,
        "title": listing.title,
        "description": listing.description,
        "tags": list(listing.tags or []),
        "price": str(listing.price) if listing.price is not None else None,
        "is_bundle": listing.is_bundle,
        "etsy_listing_id": listing.etsy_listing_id,
        "error_message": listing.error_message,
        "created_at": listing.created_at.isoformat()
    }


def _review_unavailable(review: dict[str, Any]) -> bool:
    return review.get("feedback") == "Review unavailable"


def _append_image_url(listing: Listing, image_url: str, cap: int | None = None) -> None:
    urls = list(listing.image_urls or [])
    urls.append(image_url)
    if cap is not None and len(urls) > cap:
        urls = urls[-cap:]
    listing.image_urls = urls


async def _generate_reviewed_image(
    product_idea: dict[str, Any],
    shop_style: str,
    claude_api_key: str,
    listing_id: UUID,
    is_high_res: bool,
    base_prompt: str | None = None
) -> tuple[str, str, dict[str, Any]]:
    prompt = base_prompt or build_image_prompt(product_idea, shop_style, is_high_res)
    prompt_choice = await choose_image_prompt_and_size(
        image_prompt=prompt,
        product_idea=product_idea,
        shop_style=shop_style,
        is_high_res=is_high_res,
        claude_api_key=claude_api_key
    )
    prompt = prompt_choice["prompt"]
    image_size = prompt_choice["size"]

    try:
        base64_data = await generate_product_image(prompt, is_high_res=is_high_res, image_size=image_size)
    except ImageGenerationError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Image generation failed. Please try again."
        ) from exc

    try:
        image_url = await upload_to_cloudinary(base64_data, str(listing_id))
    except CloudinaryUploadError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Could not save image. Please try again."
        ) from exc

    claude_review = await review_image(prompt, product_idea, claude_api_key)
    return image_url, prompt, claude_review


@router.get("", response_model=PaginatedListingsResponse)
def list_listings(
    status_filter: ListingStatus | None = Query(default=None, alias="status"),
    page: int = Query(default=1, ge=1),
    per_page: int = Query(default=20, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> PaginatedListingsResponse:
    shop = get_primary_shop(db, current_user)
    if not shop:
        return PaginatedListingsResponse(listings=[], total=0, page=page, per_page=per_page)

    conditions = [Listing.shop_id == shop.id]
    if status_filter:
        conditions.append(Listing.status == status_filter)

    total = db.scalar(select(func.count()).select_from(Listing).where(*conditions)) or 0
    listings = db.scalars(
        select(Listing)
        .where(*conditions)
        .order_by(Listing.created_at.desc())
        .offset((page - 1) * per_page)
        .limit(per_page)
    ).all()
    return PaginatedListingsResponse(
        listings=[_listing_out_dict(listing) for listing in listings],
        total=total,
        page=page,
        per_page=per_page
    )


@router.post("/generate-image", response_model=ImageGenerationResponse)
async def generate_image(
    payload: GenerateImageRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> ImageGenerationResponse:
    shop = _require_shop(current_user, db)
    claude_api_key = _require_claude_key(shop)
    product_idea = _apply_product_overrides(_product_idea_from_analysis(shop, payload.product_idea_index), payload)
    listing = _owned_listing(db, shop, payload.listing_id) if payload.listing_id else None
    _require_image_generation_allowed(current_user, listing, payload.is_high_res)

    if listing is None:
        listing = Listing(
            shop_id=shop.id,
            status=ListingStatus.DRAFT,
            image_urls=[],
            title=str(product_idea.get("title") or "Untitled listing")[:140],
            tags=_target_keywords(product_idea),
            price=_suggested_price(product_idea)
        )
        db.add(listing)
        db.flush()
    else:
        if payload.product_title:
            listing.title = payload.product_title.strip()[:140]
        if payload.keywords:
            listing.tags = [keyword.strip() for keyword in payload.keywords if keyword.strip()][:13]
        if payload.estimated_price is not None:
            listing.price = payload.estimated_price

    image_url, prompt, claude_review = await _generate_reviewed_image(
        product_idea=product_idea,
        shop_style=_shop_style(shop, payload.style_notes),
        claude_api_key=claude_api_key,
        listing_id=listing.id,
        is_high_res=payload.is_high_res
    )
    _append_image_url(listing, image_url)
    listing.image_prompt = prompt
    listing.claude_review_json = claude_review
    db.add(listing)
    db.commit()
    db.refresh(listing)

    return ImageGenerationResponse(
        listing_id=listing.id,
        image_url=image_url,
        claude_review=claude_review,
        image_urls=listing.image_urls,
        review_unavailable=_review_unavailable(claude_review)
    )


@router.post("/{listing_id}/regenerate-image", response_model=RegenerateImageResponse)
async def regenerate_image(
    listing_id: UUID,
    payload: RegenerateImageRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> RegenerateImageResponse:
    shop = _require_shop(current_user, db)
    claude_api_key = _require_claude_key(shop)
    listing = _owned_listing(db, shop, listing_id)
    _require_image_generation_allowed(current_user, listing, is_high_res=False)

    product_idea = {
        "title": listing.title or "Etsy product",
        "targetKeywords": listing.tags or [],
        "suggestedPrice": float(listing.price) if listing.price is not None else None
    }
    original_prompt = listing.image_prompt or build_image_prompt(product_idea, _shop_style(shop, None), False)
    improved_prompt = (listing.claude_review_json or {}).get("improvedPrompt") if listing.claude_review_json else None
    prompt = str(improved_prompt or original_prompt) if payload.use_improved_prompt else original_prompt
    image_url, prompt, claude_review = await _generate_reviewed_image(
        product_idea=product_idea,
        shop_style=_shop_style(shop, None),
        claude_api_key=claude_api_key,
        listing_id=listing.id,
        is_high_res=False,
        base_prompt=prompt
    )
    _append_image_url(listing, image_url, cap=10)
    listing.image_prompt = prompt
    listing.claude_review_json = claude_review
    db.add(listing)
    db.commit()
    db.refresh(listing)
    return RegenerateImageResponse(
        image_url=image_url,
        claude_review=claude_review,
        image_urls=listing.image_urls,
        review_unavailable=_review_unavailable(claude_review)
    )


@router.post("/{listing_id}/set-high-res", response_model=HighResImageResponse)
async def set_high_res(
    listing_id: UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> HighResImageResponse:
    shop = _require_shop(current_user, db)
    claude_api_key = _require_claude_key(shop)
    listing = _owned_listing(db, shop, listing_id)
    _require_image_generation_allowed(current_user, listing, is_high_res=True)
    product_idea = {
        "title": listing.title or "Etsy product",
        "targetKeywords": listing.tags or [],
        "suggestedPrice": float(listing.price) if listing.price is not None else None
    }
    image_url, prompt, claude_review = await _generate_reviewed_image(
        product_idea=product_idea,
        shop_style=_shop_style(shop, None),
        claude_api_key=claude_api_key,
        listing_id=listing.id,
        is_high_res=True,
        base_prompt=listing.image_prompt
    )
    _append_image_url(listing, image_url, cap=10)
    listing.image_prompt = prompt
    listing.claude_review_json = claude_review
    db.add(listing)
    db.commit()
    db.refresh(listing)
    return HighResImageResponse(image_url=image_url, image_urls=listing.image_urls)


@router.get("/{listing_id}/images", response_model=ListingImagesResponse)
def get_listing_images(
    listing_id: UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> ListingImagesResponse:
    shop = _require_shop(current_user, db)
    listing = _owned_listing(db, shop, listing_id)
    image_urls = list(listing.image_urls or [])
    return ListingImagesResponse(
        image_urls=image_urls,
        current_image_url=listing.primary_image_url or (image_urls[-1] if image_urls else None),
        claude_review=listing.claude_review_json,
        image_prompt=listing.image_prompt
    )


@router.patch("/{listing_id}/approve-image", response_model=ApproveImageResponse)
def approve_image(
    listing_id: UUID,
    payload: ApproveImageRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> ApproveImageResponse:
    shop = _require_shop(current_user, db)
    listing = _owned_listing(db, shop, listing_id)
    if payload.approved_image_url not in (listing.image_urls or []):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Image does not belong to this listing.")

    listing.primary_image_url = payload.approved_image_url
    listing.status = ListingStatus.IMAGE_APPROVED
    db.add(listing)
    db.commit()
    return ApproveImageResponse(success=True)


@router.post("/{listing_id}/generate-video", response_model=GenerateVideoResponse)
async def generate_video(
    listing_id: UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> GenerateVideoResponse:
    _require_video_generation_allowed(current_user)
    shop = _require_shop(current_user, db)
    listing = _owned_listing(db, shop, listing_id)
    image_urls = _video_image_urls(listing)
    product_idea = _listing_product_idea(shop, listing)

    try:
        video_bytes = await generate_listing_video(
            image_urls=image_urls,
            product_idea=product_idea,
            shop_style=_shop_style(shop, None)
        )
    except VideoGenerationError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Video generation failed. Please try again."
        ) from exc

    try:
        video_url = await upload_video(video_bytes, str(listing.id))
    except VideoUploadError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Video generation failed. Please try again."
        ) from exc

    listing.video_url = video_url
    db.add(listing)
    db.commit()
    return GenerateVideoResponse(video_url=video_url)


@router.post("/{listing_id}/generate-copy", response_model=GenerateCopyResponse)
async def generate_copy(
    listing_id: UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> GenerateCopyResponse:
    shop = _require_shop(current_user, db)
    claude_api_key = _require_claude_key(shop)
    listing = _owned_listing(db, shop, listing_id)
    product_idea = _listing_product_idea(shop, listing)

    try:
        copy = await generate_listing_copy(product_idea, _shop_analysis(shop), claude_api_key)
    except (CopyGenerationError, CopyJSONParseError) as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Copy generation failed. Check your Claude API key in settings."
        ) from exc

    listing.title = str(copy["title"])[:140]
    listing.description = str(copy["description"])
    listing.tags = _clean_tags(copy["tags"])
    listing.price = _copy_price(copy.get("suggestedPrice"))
    listing.status = ListingStatus.COPY_READY
    db.add(listing)
    db.commit()

    return GenerateCopyResponse(
        title=listing.title,
        description=listing.description,
        tags=listing.tags,
        suggestedPrice=float(listing.price) if listing.price is not None else float(copy["suggestedPrice"])
    )


@router.patch("/{listing_id}/copy", response_model=SuccessResponse)
def update_copy(
    listing_id: UUID,
    payload: ListingCopyUpdateRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> SuccessResponse:
    shop = _require_shop(current_user, db)
    listing = _owned_listing(db, shop, listing_id)
    updates = payload.model_dump(exclude_unset=True)

    if "title" in updates:
        listing.title = payload.title.strip() if payload.title else None
    if "description" in updates:
        listing.description = payload.description
    if "tags" in updates:
        listing.tags = _clean_tags(payload.tags or [])
    if "price" in updates:
        listing.price = payload.price

    if listing.title and listing.description:
        listing.status = ListingStatus.COPY_READY

    db.add(listing)
    db.commit()
    return SuccessResponse(success=True)


@router.get("/{listing_id}/package", response_model=ListingPackageResponse)
def get_package(
    listing_id: UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> ListingPackageResponse:
    shop = _require_shop(current_user, db)
    listing = _owned_listing(db, shop, listing_id)
    return ListingPackageResponse(
        listing_id=listing.id,
        image_urls=list(listing.image_urls or []),
        primary_image_url=listing.primary_image_url,
        video_url=listing.video_url,
        title=listing.title,
        description=listing.description,
        tags=list(listing.tags or []),
        price=_price_as_float(listing.price),
        status=listing.status.value,
        is_bundle=listing.is_bundle
    )


@router.patch("/{listing_id}/bundle", response_model=SuccessResponse)
def update_bundle(
    listing_id: UUID,
    payload: BundleRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> SuccessResponse:
    shop = _require_shop(current_user, db)
    listing = _owned_listing(db, shop, listing_id)
    listing.is_bundle = payload.is_bundle
    db.add(listing)
    db.commit()
    return SuccessResponse(success=True)


@router.post("/{listing_id}/upload", response_model=ListingUploadResponse)
async def upload_listing(
    listing_id: UUID,
    payload: ListingUploadRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> ListingUploadResponse:
    shop = _require_shop(current_user, db)
    listing = _owned_listing(db, shop, listing_id)

    if payload.mode == "manual":
        listing.status = ListingStatus.QUEUED_MANUAL
        listing.error_message = None
        db.add(listing)
        db.commit()
        return ListingUploadResponse(message="Saved to manual review queue")

    if not payload.disclaimer_accepted:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="You must accept the disclaimer to continue.")

    _require_etsy_connection(shop)
    _require_upload_ready(listing)
    listing.status = ListingStatus.QUEUED
    listing.error_message = None
    db.add(listing)
    db.commit()

    job_id = await enqueue_upload_job(listing.id, current_user.id, shop.id)
    return ListingUploadResponse(job_id=job_id, message="Upload queued")


@router.get("/{listing_id}/status", response_model=ListingStatusResponse)
def get_listing_status(
    listing_id: UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> ListingStatusResponse:
    shop = _require_shop(current_user, db)
    listing = _owned_listing(db, shop, listing_id)
    etsy_listing_url = (
        f"https://www.etsy.com/listing/{listing.etsy_listing_id}"
        if listing.etsy_listing_id else None
    )
    return ListingStatusResponse(
        status=listing.status.value,
        etsy_listing_id=listing.etsy_listing_id,
        etsy_listing_url=etsy_listing_url,
        error_message=listing.error_message
    )


@router.get("/{listing_id}/download")
async def download_listing_package(
    listing_id: UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> StreamingResponse:
    shop = _require_shop(current_user, db)
    listing = _owned_listing(db, shop, listing_id)
    listing_data = listing_to_upload_dict(listing)
    listing_data["description"] = listing.description

    try:
        zip_bytes = await create_listing_zip(listing_data)
    except ZipCreationError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Could not create download. Please try again."
        ) from exc

    return StreamingResponse(
        BytesIO(zip_bytes),
        media_type="application/zip",
        headers={"Content-Disposition": f'attachment; filename="listing-{listing_id}.zip"'}
    )


@router.delete("/{listing_id}", response_model=SuccessResponse)
def delete_listing(
    listing_id: UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> SuccessResponse:
    shop = _require_shop(current_user, db)
    listing = _owned_listing(db, shop, listing_id)
    if listing.status in {ListingStatus.QUEUED, ListingStatus.LIVE}:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot delete a listing that is currently uploading."
        )
    db.delete(listing)
    db.commit()
    return SuccessResponse(success=True)


@router.post("/bulk-queue", response_model=BulkQueueResponse)
async def bulk_queue(
    payload: BulkQueueRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> BulkQueueResponse:
    if not payload.disclaimer_accepted:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="You must accept the disclaimer to continue.")

    shop = _require_shop(current_user, db)
    _require_etsy_connection(shop)

    queued_count = 0
    for index, listing_id in enumerate(payload.listing_ids):
        listing = _owned_listing(db, shop, listing_id)
        _require_upload_ready(listing)
        listing.status = ListingStatus.QUEUED
        listing.error_message = None
        db.add(listing)
        db.commit()
        await enqueue_upload_job(listing.id, current_user.id, shop.id, delay_seconds=index * 60)
        queued_count += 1

    return BulkQueueResponse(queued_count=queued_count)
