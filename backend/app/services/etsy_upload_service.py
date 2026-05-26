import asyncio
from typing import Any

import httpx
from sqlalchemy.orm import Session

from backend.app.core.config import get_settings
from backend.app.models.listing import Listing
from backend.app.models.shop import Shop
from backend.app.services.etsy import fetch_primary_shop, get_valid_etsy_access_token, refresh_etsy_token

ETSY_API_BASE_URL = "https://openapi.etsy.com/v3/application"
REQUEST_DELAY_SECONDS = 0.12


class EtsyUploadError(Exception):
    pass


class EtsyUploadAuthError(EtsyUploadError):
    pass


def _headers(access_token: str) -> dict[str, str]:
    return {
        "Authorization": f"Bearer {access_token}",
        "x-api-key": get_settings().etsy_client_id
    }


def _form_headers(access_token: str) -> dict[str, str]:
    headers = _headers(access_token)
    headers["Content-Type"] = "application/x-www-form-urlencoded"
    return headers


async def _etsy_request(
    method: str,
    path: str,
    access_token: str,
    *,
    data: dict[str, Any] | None = None,
    files: dict[str, Any] | None = None,
    headers: dict[str, str] | None = None
) -> dict[str, Any]:
    await asyncio.sleep(REQUEST_DELAY_SECONDS)
    async with httpx.AsyncClient(timeout=60) as client:
        try:
            response = await client.request(
                method,
                f"{ETSY_API_BASE_URL}{path}",
                headers=headers or _headers(access_token),
                data=data,
                files=files
            )
        except httpx.HTTPError as exc:
            raise EtsyUploadError("Etsy upload request failed") from exc

    if response.status_code in {401, 403}:
        raise EtsyUploadAuthError("Etsy OAuth token expired")
    if response.status_code == 429:
        raise EtsyUploadError("Etsy API rate limit hit")
    if response.status_code >= 400:
        raise EtsyUploadError("Etsy upload request failed")
    if not response.content:
        return {}
    try:
        return response.json()
    except ValueError:
        return {}


async def _download_file(url: str) -> tuple[bytes, str]:
    async with httpx.AsyncClient(timeout=60, follow_redirects=True) as client:
        try:
            response = await client.get(url)
        except httpx.HTTPError as exc:
            raise EtsyUploadError("Could not download listing asset") from exc
    if response.status_code >= 400 or not response.content:
        raise EtsyUploadError("Could not download listing asset")
    content_type = response.headers.get("content-type") or "application/octet-stream"
    return response.content, content_type


def _listing_payload(listing_data: dict[str, Any]) -> dict[str, Any]:
    listing_type = str(listing_data.get("type") or "download").lower()
    return {
        "title": str(listing_data.get("title") or "Untitled listing")[:140],
        "description": str(listing_data.get("description") or ""),
        "price": str(listing_data.get("price") or "0.00"),
        "quantity": str(listing_data.get("quantity") or 999),
        "tags": ",".join(str(tag) for tag in (listing_data.get("tags") or [])[:13]),
        "type": listing_type,
        "taxonomy_id": str(listing_data.get("taxonomy_id") or 1),
        "who_made": str(listing_data.get("who_made") or "i_did"),
        "when_made": str(listing_data.get("when_made") or "made_to_order"),
        "is_supply": str(bool(listing_data.get("is_supply", False))).lower(),
        "should_auto_renew": str(bool(listing_data.get("should_auto_renew", True))).lower()
    }


async def create_etsy_listing(listing_data: dict[str, Any], access_token: str, shop_id: str) -> str:
    payload = await _etsy_request(
        "POST",
        f"/shops/{shop_id}/listings",
        access_token,
        data=_listing_payload(listing_data),
        headers=_form_headers(access_token)
    )
    listing_id = payload.get("listing_id")
    if not listing_id:
        raise EtsyUploadError("Etsy returned no listing id")
    return str(listing_id)


async def upload_listing_images(etsy_listing_id: str, image_urls: list[str], access_token: str, shop_id: str) -> None:
    for index, image_url in enumerate(image_urls):
        image_bytes, content_type = await _download_file(image_url)
        files = {
            "image": (f"listing-image-{index + 1}.jpg", image_bytes, content_type)
        }
        data = {"rank": str(index + 1)}
        await _etsy_request(
            "POST",
            f"/shops/{shop_id}/listings/{etsy_listing_id}/images",
            access_token,
            data=data,
            files=files
        )
        await asyncio.sleep(0.1)


async def upload_listing_video(etsy_listing_id: str, video_url: str, access_token: str, shop_id: str) -> None:
    video_bytes, content_type = await _download_file(video_url)
    files = {
        "video": ("listing-video.mp4", video_bytes, content_type if content_type.startswith("video/") else "video/mp4")
    }
    data = {"name": "listing-video.mp4"}
    await _etsy_request(
        "POST",
        f"/shops/{shop_id}/listings/{etsy_listing_id}/videos",
        access_token,
        data=data,
        files=files
    )


async def upload_listing_file(etsy_listing_id: str, file_url: str, access_token: str, shop_id: str) -> None:
    file_bytes, content_type = await _download_file(file_url)
    files = {
        "file": ("digital-product.pdf", file_bytes, content_type if content_type == "application/pdf" else "application/pdf")
    }
    data = {"name": "digital-product.pdf"}
    await _etsy_request(
        "POST",
        f"/shops/{shop_id}/listings/{etsy_listing_id}/files",
        access_token,
        data=data,
        files=files
    )


async def publish_listing(etsy_listing_id: str, access_token: str, shop_id: str) -> None:
    await _etsy_request(
        "PATCH",
        f"/shops/{shop_id}/listings/{etsy_listing_id}",
        access_token,
        data={"state": "active"},
        headers=_form_headers(access_token)
    )


async def full_upload_flow(listing: dict[str, Any], access_token: str, shop_id: str) -> str:
    etsy_listing_id = await create_etsy_listing(listing, access_token, shop_id)
    await upload_listing_images(etsy_listing_id, listing.get("image_urls") or [], access_token, shop_id)
    if listing.get("video_url"):
        await upload_listing_video(etsy_listing_id, str(listing["video_url"]), access_token, shop_id)
    if listing.get("pdf_url"):
        await upload_listing_file(etsy_listing_id, str(listing["pdf_url"]), access_token, shop_id)
    await publish_listing(etsy_listing_id, access_token, shop_id)
    return etsy_listing_id


async def get_etsy_shop_id(db: Session, shop: Shop, access_token: str) -> str:
    if shop.etsy_shop_id:
        return shop.etsy_shop_id
    shop_data = await fetch_primary_shop(access_token)
    shop_id = shop_data.get("shop_id") if shop_data else None
    if not shop_id:
        raise EtsyUploadError("Could not identify Etsy shop")
    shop.etsy_shop_id = str(shop_id)
    db.add(shop)
    db.commit()
    db.refresh(shop)
    return str(shop_id)


def listing_to_upload_dict(listing: Listing) -> dict[str, Any]:
    image_urls = list(listing.image_urls or [])
    if listing.primary_image_url and listing.primary_image_url in image_urls:
        image_urls = [listing.primary_image_url] + [url for url in image_urls if url != listing.primary_image_url]
    return {
        "title": listing.title,
        "description": listing.description,
        "price": float(listing.price) if listing.price is not None else None,
        "quantity": 999,
        "tags": list(listing.tags or []),
        "type": "download",
        "image_urls": image_urls,
        "pdf_url": listing.pdf_url,
        "video_url": listing.video_url
    }


async def full_upload_flow_with_refresh(db: Session, shop: Shop, listing: Listing) -> str:
    access_token = await get_valid_etsy_access_token(db, shop)
    shop_id = await get_etsy_shop_id(db, shop, access_token)
    listing_data = listing_to_upload_dict(listing)
    try:
        return await full_upload_flow(listing_data, access_token, shop_id)
    except EtsyUploadAuthError:
        refreshed_token = await refresh_etsy_token(db, shop)
        shop_id = await get_etsy_shop_id(db, shop, refreshed_token)
        return await full_upload_flow(listing_data, refreshed_token, shop_id)
