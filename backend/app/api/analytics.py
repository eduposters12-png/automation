from datetime import datetime, timezone
from typing import Literal

import httpx
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from backend.app.core.config import get_settings
from backend.app.core.deps import get_current_user
from backend.app.core.security import decrypt_secret
from backend.app.db.session import get_db
from backend.app.models.listing import Listing, ListingStatus
from backend.app.models.user import User
from backend.app.services.etsy import get_valid_etsy_access_token
from backend.app.services.etsy_upload_service import ETSY_API_BASE_URL, get_etsy_shop_id
from backend.app.services.shops import get_primary_shop
from backend.app.services.usage_service import get_usage_this_month, usage_with_limits

router = APIRouter(prefix="/analytics", tags=["analytics"])
shop_router = APIRouter(prefix="/shop", tags=["shop"])


class TestConnectionRequest(BaseModel):
    key_type: Literal["etsy", "claude"]


@router.get("/dashboard")
def analytics_dashboard(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> dict:
    shop = get_primary_shop(db, current_user)
    listing_query = select(Listing).where(Listing.shop_id == shop.id) if shop else select(Listing).where(False)
    total_listings = db.scalar(select(func.count()).select_from(listing_query.subquery())) or 0
    live_listings = db.scalar(
        select(func.count()).select_from(Listing).where(
            Listing.shop_id == shop.id,
            Listing.status == ListingStatus.LIVE
        )
    ) if shop else 0
    recent = db.scalars(
        select(Listing)
        .where(Listing.shop_id == shop.id)
        .order_by(Listing.created_at.desc())
        .limit(5)
    ).all() if shop else []

    return {
        "total_listings": total_listings,
        "live_listings": live_listings or 0,
        "usage_this_month": usage_with_limits(current_user, db),
        "plan": current_user.plan.value,
        "recent_listings": [
            {
                "id": str(listing.id),
                "title": listing.title,
                "status": listing.status.value,
                "primary_image_url": listing.primary_image_url,
                "created_at": listing.created_at.isoformat()
            }
            for listing in recent
        ],
        "shop": {
            "niche": shop.niche if shop else None,
            "last_analyzed_at": shop.last_analyzed_at.isoformat() if shop and shop.last_analyzed_at else None
        }
    }


@router.get("/usage")
def analytics_usage(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> dict:
    return {
        "usage": get_usage_this_month(current_user.id, db),
        "usage_with_limits": usage_with_limits(current_user, db),
        "plan": current_user.plan.value
    }


@shop_router.post("/test-connection")
async def test_connection(
    payload: TestConnectionRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> dict[str, str | bool]:
    shop = get_primary_shop(db, current_user)
    if not shop:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Connect your Etsy shop first")

    if payload.key_type == "etsy":
        try:
            access_token = await get_valid_etsy_access_token(db, shop)
            etsy_shop_id = await get_etsy_shop_id(db, shop, access_token)
            async with httpx.AsyncClient(timeout=20) as client:
                response = await client.get(
                    f"{ETSY_API_BASE_URL}/shops/{etsy_shop_id}",
                    headers={
                        "Authorization": f"Bearer {access_token}",
                        "x-api-key": get_settings().etsy_client_id
                    }
                )
            if response.status_code >= 400:
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Etsy connection failed")
        except HTTPException:
            raise
        except Exception as exc:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Etsy connection failed") from exc
        return {"success": True, "message": "Etsy shop connected successfully"}

    if not shop.claude_api_key_encrypted:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Claude API key is missing")
    claude_key = decrypt_secret(shop.claude_api_key_encrypted)
    try:
        async with httpx.AsyncClient(timeout=20) as client:
            response = await client.post(
                "https://api.anthropic.com/v1/messages",
                headers={
                    "x-api-key": claude_key,
                    "anthropic-version": "2023-06-01",
                    "Content-Type": "application/json"
                },
                json={
                    "model": "claude-sonnet-4-5",
                    "max_tokens": 10,
                    "messages": [{"role": "user", "content": "Hello"}]
                }
            )
        if response.status_code >= 400:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Claude API key test failed")
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Claude API key test failed") from exc
    return {"success": True, "message": "Claude API key is working"}


def health_payload() -> dict[str, str]:
    return {"status": "ok", "timestamp": datetime.now(timezone.utc).isoformat()}
