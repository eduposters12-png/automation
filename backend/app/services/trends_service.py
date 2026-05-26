import re
from datetime import datetime, timedelta, timezone
from typing import Any

import httpx
from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.app.core.config import get_settings
from backend.app.models.trends_cache import TrendsCache

SERPER_SEARCH_URL = "https://google.serper.dev/search"
CACHE_TTL = timedelta(hours=24)


class TrendsFetchError(Exception):
    pass


def normalize_niche(niche: str) -> str:
    normalized = re.sub(r"[^a-z0-9\s-]", " ", niche.lower())
    normalized = re.sub(r"\s+", " ", normalized).strip()
    return (normalized or "etsy products")[:255]


def _cached_at_is_fresh(cached_at: datetime) -> bool:
    if cached_at.tzinfo is None:
        cached_at = cached_at.replace(tzinfo=timezone.utc)
    return cached_at >= datetime.now(timezone.utc) - CACHE_TTL


def _clean_idea(text: str) -> str:
    text = re.sub(r"\s+", " ", text).strip(" -|:")
    text = re.sub(r"\b(2025|2026)\b", "", text, flags=re.IGNORECASE)
    return re.sub(r"\s+", " ", text).strip(" -|:")[:160]


def _extract_ideas(payloads: list[dict[str, Any]]) -> list[str]:
    ideas: list[str] = []
    seen: set[str] = set()

    def add_idea(value: str | None) -> None:
        if not value:
            return
        idea = _clean_idea(value)
        key = idea.lower()
        if len(idea) < 5 or key in seen:
            return
        seen.add(key)
        ideas.append(idea)

    for payload in payloads:
        for result in payload.get("organic", []) or []:
            if isinstance(result, dict):
                add_idea(result.get("title"))
        for result in payload.get("relatedSearches", []) or []:
            if isinstance(result, dict):
                add_idea(result.get("query") or result.get("value"))
        for result in payload.get("peopleAlsoAsk", []) or []:
            if isinstance(result, dict):
                add_idea(result.get("question"))

    return ideas[:10]


async def _fetch_serper_results(niche: str) -> list[str]:
    settings = get_settings()
    if not settings.serper_api_key:
        raise TrendsFetchError("SERPER_API_KEY is not configured")

    queries = [
        f"trending etsy products 2025 {niche}",
        f"best selling etsy {niche} product ideas"
    ]
    payloads: list[dict[str, Any]] = []
    headers = {
        "X-API-KEY": settings.serper_api_key,
        "Content-Type": "application/json"
    }

    async with httpx.AsyncClient(timeout=20) as client:
        for query in queries:
            try:
                response = await client.post(SERPER_SEARCH_URL, headers=headers, json={"q": query, "num": 10})
            except httpx.HTTPError as exc:
                raise TrendsFetchError("Serper request failed") from exc
            if response.status_code >= 400:
                raise TrendsFetchError("Serper request failed")
            try:
                payloads.append(response.json())
            except ValueError as exc:
                raise TrendsFetchError("Serper returned invalid JSON") from exc

    ideas = _extract_ideas(payloads)
    if not ideas:
        raise TrendsFetchError("Serper returned no trend ideas")
    return ideas


async def fetch_trends(niche: str, db: Session | None = None) -> list[str]:
    normalized_niche = normalize_niche(niche)

    if db is not None:
        cached = db.scalar(select(TrendsCache).where(TrendsCache.niche == normalized_niche))
        if cached and _cached_at_is_fresh(cached.cached_at):
            return list(cached.trends_json or [])

    trends = await _fetch_serper_results(normalized_niche)

    if db is not None:
        cached = db.scalar(select(TrendsCache).where(TrendsCache.niche == normalized_niche))
        if cached:
            cached.trends_json = trends
            cached.cached_at = datetime.now(timezone.utc)
        else:
            cached = TrendsCache(niche=normalized_niche, trends_json=trends, cached_at=datetime.now(timezone.utc))
        db.add(cached)
        db.commit()

    return trends
