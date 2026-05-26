import secrets
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response, status
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session

from backend.app.core.config import get_settings
from backend.app.core.deps import get_current_user
from backend.app.core.security import encrypt_secret
from backend.app.db.session import get_db
from backend.app.models.shop import Shop
from backend.app.models.user import User
from backend.app.schemas.etsy import EtsyConnectionStatus, EtsyDisconnectResponse
from backend.app.services.etsy import (
    create_authorization_url,
    create_pkce_pair,
    exchange_code_for_token,
    fetch_primary_shop
)
from backend.app.services.shops import get_or_create_primary_shop, get_primary_shop

router = APIRouter(prefix="/etsy", tags=["etsy"])

STATE_COOKIE = "etsy_oauth_state"
VERIFIER_COOKIE = "etsy_code_verifier"


@router.get("/connect")
def connect_etsy(
    response: Response,
    current_user: User = Depends(get_current_user)
) -> dict[str, str]:
    state = secrets.token_urlsafe(32)
    verifier, challenge = create_pkce_pair()
    auth_url = create_authorization_url(state=state, code_challenge=challenge)
    settings = get_settings()

    cookie_options = {
        "max_age": 600,
        "httponly": True,
        "secure": settings.cookie_secure,
        "samesite": "lax",
        "domain": settings.cookie_domain
    }
    response.set_cookie(STATE_COOKIE, state, **cookie_options)
    response.set_cookie(VERIFIER_COOKIE, verifier, **cookie_options)
    return {"auth_url": auth_url}


@router.get("/callback")
async def etsy_callback(
    request: Request,
    code: str | None = Query(default=None),
    state: str | None = Query(default=None),
    error: str | None = Query(default=None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> RedirectResponse:
    settings = get_settings()
    frontend_url = str(settings.frontend_url).rstrip("/")
    redirect_url = f"{frontend_url}/onboarding"
    response = RedirectResponse(url=redirect_url, status_code=status.HTTP_303_SEE_OTHER)
    response.delete_cookie(STATE_COOKIE, domain=settings.cookie_domain)
    response.delete_cookie(VERIFIER_COOKIE, domain=settings.cookie_domain)

    if error:
        response.headers["location"] = f"{redirect_url}?etsy=denied"
        return response

    expected_state = request.cookies.get(STATE_COOKIE)
    verifier = request.cookies.get(VERIFIER_COOKIE)
    if not code or not state or not expected_state or not verifier or not secrets.compare_digest(state, expected_state):
        response.headers["location"] = f"{redirect_url}?etsy=invalid"
        return response

    try:
        token_data = await exchange_code_for_token(code=code, code_verifier=verifier)
    except Exception:
        response.headers["location"] = f"{redirect_url}?etsy=failed"
        return response

    access_token = token_data["access_token"]
    refresh_token = token_data["refresh_token"]
    shop_data = await fetch_primary_shop(access_token)

    shop: Shop = get_or_create_primary_shop(db, current_user)
    shop.etsy_access_token_encrypted = encrypt_secret(access_token)
    shop.etsy_refresh_token_encrypted = encrypt_secret(refresh_token)
    shop.etsy_token_expires_at = datetime.now(timezone.utc) + timedelta(
        seconds=int(token_data.get("expires_in", 3600))
    )
    if shop_data:
        if shop_data.get("shop_id"):
            shop.etsy_shop_id = str(shop_data.get("shop_id"))
        shop.shop_name = shop_data.get("shop_name") or shop.shop_name
        shop.shop_url = shop_data.get("url") or shop.shop_url
    db.add(shop)
    db.commit()

    response.headers["location"] = f"{redirect_url}?etsy=connected"
    return response


@router.get("/connection-status", response_model=EtsyConnectionStatus)
def etsy_connection_status(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> EtsyConnectionStatus:
    shop = get_primary_shop(db, current_user)
    if not shop or not shop.etsy_access_token_encrypted:
        return EtsyConnectionStatus(connected=False)

    return EtsyConnectionStatus(
        connected=True,
        shop_name=shop.shop_name,
        shop_url=shop.shop_url,
        etsy_shop_id=shop.etsy_shop_id,
        connected_at=None
    )


@router.post("/disconnect", response_model=EtsyDisconnectResponse)
def disconnect_etsy(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> EtsyDisconnectResponse:
    shop = get_primary_shop(db, current_user)
    if not shop:
        return EtsyDisconnectResponse(success=True, message="No shop connected")

    shop.etsy_access_token_encrypted = None
    shop.etsy_refresh_token_encrypted = None
    shop.etsy_token_expires_at = None
    shop.etsy_shop_id = None
    shop.shop_name = None
    db.add(shop)
    db.commit()

    return EtsyDisconnectResponse(success=True, message="Etsy account disconnected successfully")
