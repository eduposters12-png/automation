from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from backend.app.core.deps import get_current_user
from backend.app.core.security import encrypt_secret
from backend.app.db.session import get_db
from backend.app.models.user import User
from backend.app.schemas.settings import SettingsResponse, SettingsUpdateRequest
from backend.app.services.shops import get_or_create_primary_shop, get_primary_shop

router = APIRouter(prefix="/settings", tags=["settings"])


@router.get("", response_model=SettingsResponse)
def get_settings(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> SettingsResponse:
    shop = get_primary_shop(db, current_user)
    return SettingsResponse(
        name=current_user.name,
        email=current_user.email,
        plan=current_user.plan.value,
        shop_name=shop.shop_name if shop else None,
        shop_url=shop.shop_url if shop else None,
        niche=shop.niche if shop else None,
        etsy_connected=bool(shop and shop.etsy_access_token_encrypted),
        claude_key_added=bool(shop and shop.claude_api_key_encrypted)
    )


@router.patch("", response_model=SettingsResponse)
def update_settings(
    payload: SettingsUpdateRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> SettingsResponse:
    shop = get_or_create_primary_shop(db, current_user)
    if payload.name is not None:
        current_user.name = payload.name.strip()
    if payload.shop_url is not None:
        shop.shop_url = payload.shop_url.strip() or None
    if payload.niche is not None:
        shop.niche = payload.niche.strip() or None
    if payload.claude_api_key:
        shop.claude_api_key_encrypted = encrypt_secret(payload.claude_api_key)

    db.add(current_user)
    db.add(shop)
    db.commit()
    db.refresh(current_user)
    db.refresh(shop)

    return SettingsResponse(
        name=current_user.name,
        email=current_user.email,
        plan=current_user.plan.value,
        shop_name=shop.shop_name,
        shop_url=shop.shop_url,
        niche=shop.niche,
        etsy_connected=bool(shop.etsy_access_token_encrypted),
        claude_key_added=bool(shop.claude_api_key_encrypted)
    )
