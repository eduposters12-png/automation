import base64
import hashlib
import secrets
from datetime import datetime, timedelta, timezone
from typing import Any
from urllib.parse import urlencode

import httpx
from sqlalchemy.orm import Session

from backend.app.core.config import get_settings
from backend.app.core.security import decrypt_secret, encrypt_secret
from backend.app.models.shop import Shop

ETSY_AUTHORIZE_URL = "https://www.etsy.com/oauth/connect"
ETSY_TOKEN_URL = "https://api.etsy.com/v3/public/oauth/token"
ETSY_API_BASE_URL = "https://api.etsy.com/v3/application"


def _base64url(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).decode("utf-8").rstrip("=")


def create_pkce_pair() -> tuple[str, str]:
    verifier = _base64url(secrets.token_bytes(32))
    challenge = _base64url(hashlib.sha256(verifier.encode("utf-8")).digest())
    return verifier, challenge


def create_authorization_url(state: str, code_challenge: str) -> str:
    settings = get_settings()
    query = urlencode(
        {
            "response_type": "code",
            "client_id": settings.etsy_client_id,
            "redirect_uri": str(settings.etsy_redirect_uri),
            "scope": settings.etsy_scopes,
            "state": state,
            "code_challenge": code_challenge,
            "code_challenge_method": "S256"
        }
    )
    return f"{ETSY_AUTHORIZE_URL}?{query}"


async def exchange_code_for_token(code: str, code_verifier: str) -> dict[str, Any]:
    settings = get_settings()
    data = {
        "grant_type": "authorization_code",
        "client_id": settings.etsy_client_id,
        "redirect_uri": str(settings.etsy_redirect_uri),
        "code": code,
        "code_verifier": code_verifier
    }
    async with httpx.AsyncClient(timeout=20) as client:
        response = await client.post(ETSY_TOKEN_URL, data=data)
        response.raise_for_status()
        return response.json()


async def refresh_etsy_token(db: Session, shop: Shop) -> str:
    if not shop.etsy_refresh_token_encrypted:
        raise ValueError("Shop is not connected to Etsy")

    settings = get_settings()
    refresh_token = decrypt_secret(shop.etsy_refresh_token_encrypted)
    data = {
        "grant_type": "refresh_token",
        "client_id": settings.etsy_client_id,
        "refresh_token": refresh_token
    }
    async with httpx.AsyncClient(timeout=20) as client:
        response = await client.post(ETSY_TOKEN_URL, data=data)
        response.raise_for_status()
        token_data = response.json()

    shop.etsy_access_token_encrypted = encrypt_secret(token_data["access_token"])
    if token_data.get("refresh_token"):
        shop.etsy_refresh_token_encrypted = encrypt_secret(token_data["refresh_token"])
    shop.etsy_token_expires_at = datetime.now(timezone.utc) + timedelta(
        seconds=int(token_data.get("expires_in", 3600))
    )
    db.add(shop)
    db.commit()
    db.refresh(shop)
    return token_data["access_token"]


async def get_valid_etsy_access_token(db: Session, shop: Shop) -> str:
    if not shop.etsy_access_token_encrypted:
        raise ValueError("Shop is not connected to Etsy")

    expires_at = shop.etsy_token_expires_at
    if expires_at and expires_at <= datetime.now(timezone.utc) + timedelta(minutes=5):
        return await refresh_etsy_token(db, shop)

    return decrypt_secret(shop.etsy_access_token_encrypted)


async def fetch_primary_shop(access_token: str) -> dict[str, Any] | None:
    settings = get_settings()
    user_id = access_token.split(".", 1)[0]
    headers = {
        "Authorization": f"Bearer {access_token}",
        "x-api-key": settings.etsy_client_id
    }
    async with httpx.AsyncClient(timeout=20) as client:
        response = await client.get(
            f"{ETSY_API_BASE_URL}/users/{user_id}/shops",
            headers=headers
        )
        if response.status_code >= 400:
            return None
        payload = response.json()

    results = payload.get("results") or []
    return results[0] if results else None
