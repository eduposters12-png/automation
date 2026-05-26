import re
from collections import Counter
from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from backend.app.core.deps import get_current_user
from backend.app.core.security import decrypt_secret
from backend.app.db.session import get_db
from backend.app.models.user import Plan, User
from backend.app.schemas.shop import ShopAnalysisResponse
from backend.app.services.claude_service import (
    ClaudeAnalysisError,
    ClaudeJSONParseError,
    analyze_shop
)
from backend.app.services.etsy import get_valid_etsy_access_token
from backend.app.services.etsy_service import (
    EtsyAPIError,
    EtsyConnectionExpiredError,
    fetch_shop_data_with_refresh
)
from backend.app.services.shops import get_primary_shop
from backend.app.services.trends_service import TrendsFetchError, fetch_trends

router = APIRouter(prefix="/shop", tags=["shop"])

COMMON_NICHE_WORDS = {
    "and", "are", "best", "digital", "etsy", "for", "from", "handmade", "listing",
    "made", "new", "our", "shop", "the", "this", "with", "your"
}


def _derive_niche(shop_niche: str | None, shop_data: dict[str, Any]) -> str:
    if shop_niche and shop_niche.strip():
        return shop_niche.strip()

    listings = shop_data.get("listings") or []
    tag_counter: Counter[str] = Counter()
    text_parts = [shop_data.get("description") or "", shop_data.get("shopName") or ""]

    for section in shop_data.get("sections") or []:
        text_parts.append(str(section.get("title") or ""))

    for listing in listings:
        text_parts.append(str(listing.get("title") or ""))
        for tag in listing.get("tags") or []:
            cleaned = str(tag).strip().lower()
            if cleaned:
                tag_counter[cleaned] += 1

    if tag_counter:
        return " ".join(tag for tag, _ in tag_counter.most_common(5))[:120]

    words = re.findall(r"[a-zA-Z][a-zA-Z-]{2,}", " ".join(text_parts).lower())
    word_counter = Counter(word for word in words if word not in COMMON_NICHE_WORDS)
    if word_counter:
        return " ".join(word for word, _ in word_counter.most_common(5))[:120]

    return "etsy products"


@router.get("/analysis", response_model=ShopAnalysisResponse, response_model_exclude_none=True)
def get_shop_analysis(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> ShopAnalysisResponse:
    shop = get_primary_shop(db, current_user)
    if not shop or not shop.analysis_json:
        return ShopAnalysisResponse(analyzed=False)

    return ShopAnalysisResponse(
        analyzed=True,
        analysis=shop.analysis_json,
        last_analyzed_at=shop.last_analyzed_at
    )


@router.post("/analyze")
async def analyze_current_shop(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> dict[str, Any]:
    if current_user.plan == Plan.FREE:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Free plan cannot use shop analysis. Please upgrade to continue."
        )

    shop = get_primary_shop(db, current_user)
    if not shop or not shop.etsy_access_token_encrypted:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Connect your Etsy shop first")
    if not shop.claude_api_key_encrypted:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Add your Claude API key first")

    try:
        access_token = await get_valid_etsy_access_token(db, shop)
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Etsy connection expired. Please reconnect your shop."
        ) from exc

    try:
        shop_data = await fetch_shop_data_with_refresh(db, shop, access_token)
    except EtsyConnectionExpiredError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Etsy connection expired. Please reconnect your shop."
        ) from exc
    except EtsyAPIError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Could not fetch shop data from Etsy."
        ) from exc

    if not shop_data.get("listings"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Your shop has no active listings yet."
        )

    niche = _derive_niche(shop.niche, shop_data)
    try:
        trends = await fetch_trends(niche, db=db)
    except TrendsFetchError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Could not fetch market trends. Please try again."
        ) from exc

    claude_api_key = decrypt_secret(shop.claude_api_key_encrypted)
    try:
        analysis = await analyze_shop(shop_data, trends, claude_api_key)
    except ClaudeAnalysisError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Claude analysis failed. Check your Claude API key in settings."
        ) from exc
    except ClaudeJSONParseError as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Claude returned invalid analysis JSON. Please try again."
        ) from exc

    shop.analysis_json = analysis
    shop.last_analyzed_at = datetime.now(timezone.utc)
    db.add(shop)
    db.commit()
    db.refresh(shop)

    return analysis
