from collections import defaultdict
from typing import Any

import httpx
from sqlalchemy.orm import Session

from backend.app.core.config import get_settings
from backend.app.models.shop import Shop
from backend.app.services.etsy import refresh_etsy_token

ETSY_API_BASE_URL = "https://openapi.etsy.com/v3/application"


class EtsyAPIError(Exception):
    def __init__(self, message: str = "Etsy API request failed", status_code: int | None = None):
        super().__init__(message)
        self.status_code = status_code


class EtsyAuthError(EtsyAPIError):
    pass


class EtsyConnectionExpiredError(EtsyAPIError):
    pass


def _etsy_headers(access_token: str) -> dict[str, str]:
    return {
        "Authorization": f"Bearer {access_token}",
        "x-api-key": get_settings().etsy_client_id
    }


async def _get_etsy(
    client: httpx.AsyncClient,
    path: str,
    access_token: str,
    params: dict[str, Any] | None = None
) -> dict[str, Any]:
    try:
        response = await client.get(
            f"{ETSY_API_BASE_URL}{path}",
            headers=_etsy_headers(access_token),
            params=params
        )
    except httpx.HTTPError as exc:
        raise EtsyAPIError("Etsy API request failed") from exc
    if response.status_code in {401, 403}:
        raise EtsyAuthError(status_code=response.status_code)
    if response.status_code >= 400:
        raise EtsyAPIError(status_code=response.status_code)
    try:
        return response.json()
    except ValueError as exc:
        raise EtsyAPIError("Etsy API returned invalid JSON") from exc


def _results(payload: dict[str, Any] | list[Any]) -> list[dict[str, Any]]:
    if isinstance(payload, list):
        return [item for item in payload if isinstance(item, dict)]
    results = payload.get("results", [])
    return [item for item in results if isinstance(item, dict)]


def _money_value(value: Any) -> float | str | None:
    if isinstance(value, dict):
        amount = value.get("amount")
        divisor = value.get("divisor") or 100
        if amount is not None:
            try:
                return round(float(amount) / float(divisor), 2)
            except (TypeError, ValueError, ZeroDivisionError):
                return None
    if value is None:
        return None
    try:
        return round(float(value), 2)
    except (TypeError, ValueError):
        return str(value)


def _normalize_listing(listing: dict[str, Any]) -> dict[str, Any]:
    tags = listing.get("tags") or []
    if not isinstance(tags, list):
        tags = []
    return {
        "listingId": str(listing.get("listing_id") or ""),
        "title": listing.get("title") or "",
        "description": listing.get("description") or "",
        "tags": [str(tag) for tag in tags if tag],
        "price": _money_value(listing.get("price")),
        "views": listing.get("views") or 0,
        "quantity": listing.get("quantity") or 0
    }


def _normalize_section(section: dict[str, Any]) -> dict[str, Any]:
    return {
        "sectionId": str(section.get("shop_section_id") or ""),
        "title": section.get("title") or ""
    }


async def _fetch_primary_shop(client: httpx.AsyncClient, access_token: str) -> dict[str, Any]:
    user_id = access_token.split(".", 1)[0]
    payload = await _get_etsy(client, f"/users/{user_id}/shops", access_token)
    shops = _results(payload)
    if not shops:
        raise EtsyAPIError("No Etsy shop found")
    return shops[0]


async def _fetch_active_listings(client: httpx.AsyncClient, shop_id: int | str, access_token: str) -> list[dict[str, Any]]:
    params = {"limit": 100}
    try:
        payload = await _get_etsy(client, f"/shops/{shop_id}/listings/active", access_token, params=params)
    except EtsyAPIError as exc:
        if exc.status_code != 404:
            raise
        payload = await _get_etsy(
            client,
            f"/shops/{shop_id}/listings",
            access_token,
            params={"limit": 100, "state": "active"}
        )
    return [_normalize_listing(listing) for listing in _results(payload)]


async def _fetch_receipt_transactions(
    client: httpx.AsyncClient,
    shop_id: int | str,
    access_token: str,
    receipts: list[dict[str, Any]]
) -> list[dict[str, Any]]:
    transactions: list[dict[str, Any]] = []
    for receipt in receipts[:20]:
        embedded = receipt.get("transactions")
        if isinstance(embedded, list):
            transactions.extend(item for item in embedded if isinstance(item, dict))
            continue

        receipt_id = receipt.get("receipt_id")
        if not receipt_id:
            continue
        payload = await _get_etsy(
            client,
            f"/shops/{shop_id}/receipts/{receipt_id}/transactions",
            access_token,
            params={"limit": 100}
        )
        transactions.extend(_results(payload))
    return transactions


def _top_sellers(transactions: list[dict[str, Any]]) -> list[dict[str, Any]]:
    sellers: dict[str, dict[str, Any]] = defaultdict(lambda: {"title": "", "quantitySold": 0, "revenue": 0.0})

    for transaction in transactions:
        listing_id = str(transaction.get("listing_id") or transaction.get("listingId") or "")
        title = transaction.get("title") or transaction.get("product_title") or transaction.get("listing_title") or ""
        key = listing_id or title
        if not key:
            continue

        try:
            quantity = int(transaction.get("quantity") or transaction.get("quantity_sold") or 1)
        except (TypeError, ValueError):
            quantity = 1

        price = _money_value(transaction.get("price") or transaction.get("transaction_price"))
        revenue = float(price) * quantity if isinstance(price, (int, float)) else 0.0
        sellers[key]["listingId"] = listing_id
        sellers[key]["title"] = title or sellers[key]["title"]
        sellers[key]["quantitySold"] += quantity
        sellers[key]["revenue"] += revenue

    ranked = sorted(sellers.values(), key=lambda item: item["quantitySold"], reverse=True)
    return [
        {
            "listingId": seller.get("listingId") or "",
            "title": seller.get("title") or "",
            "quantitySold": seller["quantitySold"],
            "revenue": round(seller["revenue"], 2)
        }
        for seller in ranked[:10]
    ]


async def fetch_shop_data(access_token: str) -> dict[str, Any]:
    async with httpx.AsyncClient(timeout=25) as client:
        shop = await _fetch_primary_shop(client, access_token)
        shop_id = shop.get("shop_id")
        if not shop_id:
            raise EtsyAPIError("Etsy shop id missing")

        sections_payload = await _get_etsy(client, f"/shops/{shop_id}/sections", access_token, params={"limit": 100})
        listings = await _fetch_active_listings(client, shop_id, access_token)
        receipts_payload = await _get_etsy(client, f"/shops/{shop_id}/receipts", access_token, params={"limit": 50})
        receipts = _results(receipts_payload)
        transactions = await _fetch_receipt_transactions(client, shop_id, access_token, receipts)

    return {
        "shopName": shop.get("shop_name") or "",
        "description": shop.get("announcement") or shop.get("title") or shop.get("description") or "",
        "sections": [_normalize_section(section) for section in _results(sections_payload)],
        "listings": listings,
        "topSellers": _top_sellers(transactions)
    }


async def fetch_shop_data_with_refresh(db: Session, shop: Shop, access_token: str) -> dict[str, Any]:
    try:
        return await fetch_shop_data(access_token)
    except EtsyAuthError as exc:
        try:
            refreshed_token = await refresh_etsy_token(db, shop)
        except Exception as refresh_exc:
            raise EtsyConnectionExpiredError(status_code=exc.status_code) from refresh_exc

    try:
        return await fetch_shop_data(refreshed_token)
    except EtsyAuthError as exc:
        raise EtsyConnectionExpiredError(status_code=exc.status_code) from exc
