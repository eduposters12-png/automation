from datetime import datetime, timezone

from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from backend.app.core.deps import get_current_user
from backend.app.core.plans import PLAN_LIMITS
from backend.app.db.session import get_db
from backend.app.models.listing import Listing
from backend.app.models.user import User
from backend.app.schemas.dashboard import DashboardStats
from backend.app.services.shops import get_primary_shop

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


@router.get("/stats", response_model=DashboardStats)
def dashboard_stats(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> DashboardStats:
    shop = get_primary_shop(db, current_user)
    month_start = datetime.now(timezone.utc).replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    total_listings = 0
    monthly_usage = 0

    if shop:
        total_listings = db.scalar(
            select(func.count()).select_from(Listing).where(Listing.shop_id == shop.id)
        ) or 0
        monthly_usage = db.scalar(
            select(func.count()).select_from(Listing).where(
                Listing.shop_id == shop.id,
                Listing.created_at >= month_start
            )
        ) or 0

    limits = PLAN_LIMITS[current_user.plan]
    return DashboardStats(
        shop_name=shop.shop_name if shop else None,
        shop_url=shop.shop_url if shop else None,
        plan=current_user.plan,
        total_listings=total_listings,
        monthly_usage=monthly_usage,
        monthly_limit=limits["listings"],
        shop_limit=limits["shops"],
        etsy_connected=bool(shop and shop.etsy_access_token_encrypted),
        claude_key_added=bool(shop and shop.claude_api_key_encrypted)
    )
