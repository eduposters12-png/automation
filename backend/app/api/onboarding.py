from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from backend.app.core.deps import get_current_user
from backend.app.core.security import encrypt_secret
from backend.app.db.session import get_db
from backend.app.models.user import User
from backend.app.schemas.onboarding import ClaudeKeyRequest, OnboardingStatus
from backend.app.services.shops import get_or_create_primary_shop, get_primary_shop

router = APIRouter(prefix="/onboarding", tags=["onboarding"])


@router.get("/status", response_model=OnboardingStatus)
def onboarding_status(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> OnboardingStatus:
    shop = get_primary_shop(db, current_user)
    etsy_connected = bool(shop and shop.etsy_access_token_encrypted)
    claude_key_added = bool(shop and shop.claude_api_key_encrypted)
    return OnboardingStatus(
        etsy_connected=etsy_connected,
        claude_key_added=claude_key_added,
        complete=etsy_connected and claude_key_added
    )


@router.post("/claude-key", response_model=OnboardingStatus)
def save_claude_key(
    payload: ClaudeKeyRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> OnboardingStatus:
    shop = get_or_create_primary_shop(db, current_user)
    shop.claude_api_key_encrypted = encrypt_secret(payload.claude_api_key)
    db.add(shop)
    db.commit()
    db.refresh(shop)

    etsy_connected = bool(shop.etsy_access_token_encrypted)
    return OnboardingStatus(
        etsy_connected=etsy_connected,
        claude_key_added=True,
        complete=etsy_connected
    )
