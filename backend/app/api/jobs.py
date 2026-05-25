from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from backend.app.core.deps import get_current_user
from backend.app.core.plans import PLAN_LIMITS
from backend.app.db.session import get_db
from backend.app.models.job import Job, JobType
from backend.app.models.listing import Listing, ListingStatus
from backend.app.models.user import User
from backend.app.schemas.jobs import AnalyzeShopRequest, GenerateListingRequest, JobOut, UploadListingRequest
from backend.app.services.etsy import get_valid_etsy_access_token
from backend.app.services.shops import get_primary_shop

router = APIRouter(prefix="/jobs", tags=["jobs"])


def _require_shop(current_user: User, db: Session):
    shop = get_primary_shop(db, current_user)
    if not shop:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Connect your Etsy shop first")
    return shop


def _monthly_listing_usage(db: Session, shop_id) -> int:
    month_start = datetime.now(timezone.utc).replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    return db.scalar(
        select(func.count()).select_from(Listing).where(
            Listing.shop_id == shop_id,
            Listing.created_at >= month_start
        )
    ) or 0


@router.get("", response_model=list[JobOut])
def list_jobs(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> list[JobOut]:
    shop = _require_shop(current_user, db)
    jobs = db.scalars(select(Job).where(Job.shop_id == shop.id).order_by(Job.created_at.desc())).all()
    return [JobOut.model_validate(job) for job in jobs]


@router.post("/analyze-shop", response_model=JobOut, status_code=status.HTTP_201_CREATED)
def analyze_shop(
    payload: AnalyzeShopRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> JobOut:
    shop = _require_shop(current_user, db)
    if not shop.etsy_access_token_encrypted:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Connect your Etsy shop first")
    if not shop.claude_api_key_encrypted:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Add your Claude API key first")

    job = Job(shop_id=shop.id, type=JobType.ANALYZE, payload_json={"focus": payload.focus})
    db.add(job)
    db.commit()
    db.refresh(job)
    return JobOut.model_validate(job)


@router.post("/generate-listing", response_model=JobOut, status_code=status.HTTP_201_CREATED)
def generate_listing(
    payload: GenerateListingRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> JobOut:
    shop = _require_shop(current_user, db)
    if not shop.claude_api_key_encrypted:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Add your Claude API key first")

    limit = PLAN_LIMITS[current_user.plan]["listings"]
    if limit is not None and _monthly_listing_usage(db, shop.id) >= limit:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Monthly listing limit reached")

    listing = Listing(
        shop_id=shop.id,
        status=ListingStatus.QUEUED,
        title=payload.product_idea[:140],
        price=payload.target_price,
        tags=[],
        image_urls=[]
    )
    db.add(listing)
    db.flush()
    job = Job(
        shop_id=shop.id,
        type=JobType.GENERATE_IMAGE,
        payload_json={
            "listing_id": str(listing.id),
            "product_idea": payload.product_idea,
            "target_price": str(payload.target_price) if payload.target_price is not None else None
        }
    )
    db.add(job)
    db.commit()
    db.refresh(job)
    return JobOut.model_validate(job)


@router.post("/upload-listing", response_model=JobOut, status_code=status.HTTP_201_CREATED)
async def upload_listing(
    payload: UploadListingRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> JobOut:
    shop = _require_shop(current_user, db)
    listing = db.get(Listing, payload.listing_id)
    if not listing or listing.shop_id != shop.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Listing not found")

    try:
        await get_valid_etsy_access_token(db, shop)
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Reconnect your Etsy shop") from exc

    listing.status = ListingStatus.QUEUED
    job = Job(
        shop_id=shop.id,
        type=JobType.UPLOAD_LISTING,
        payload_json={"listing_id": str(listing.id)}
    )
    db.add(listing)
    db.add(job)
    db.commit()
    db.refresh(job)
    return JobOut.model_validate(job)
