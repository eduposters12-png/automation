import asyncio
import hashlib
from datetime import datetime, timedelta, timezone
from typing import Any
from uuid import UUID

import httpx

ANTHROPIC_MESSAGES_URL = "https://api.anthropic.com/v1/messages"
ANTHROPIC_VERSION = "2023-06-01"
CLAUDE_BALANCE_MODEL = "claude-haiku-4-5-20251001"
CACHE_TTL = timedelta(seconds=60)

_CACHE: dict[str, dict[str, Any]] = {}
_LOCKS: dict[str, asyncio.Lock] = {}


def _cache_key(claude_api_key: str, user_id: UUID | str | None = None) -> str:
    if user_id is not None:
        return f"user:{user_id}"
    key_hash = hashlib.sha256(claude_api_key.encode("utf-8")).hexdigest()
    return f"key:{key_hash}"


def _cached_result(key: str) -> dict[str, Any] | None:
    entry = _CACHE.get(key)
    if not entry:
        return None

    checked_at = entry["checked_at"]
    if datetime.now(timezone.utc) - checked_at <= CACHE_TTL:
        return entry["result"]

    _CACHE.pop(key, None)
    return None


def _store_result(key: str, result: dict[str, Any]) -> dict[str, Any]:
    _CACHE[key] = {"result": result, "checked_at": datetime.now(timezone.utc)}
    return result


def _error_payload(response: httpx.Response) -> tuple[str, str, str]:
    try:
        response_json = response.json()
    except ValueError:
        response_json = {}

    error = response_json.get("error") if isinstance(response_json, dict) else {}
    if not isinstance(error, dict):
        error = {}

    return (
        str(error.get("type") or ""),
        str(error.get("message") or ""),
        response.text or ""
    )


async def _probe_claude_key(claude_api_key: str) -> dict[str, Any]:
    headers = {
        "x-api-key": claude_api_key,
        "anthropic-version": ANTHROPIC_VERSION,
        "content-type": "application/json"
    }
    payload = {
        "model": CLAUDE_BALANCE_MODEL,
        "max_tokens": 1,
        "messages": [{"role": "user", "content": "hi"}]
    }

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.post(ANTHROPIC_MESSAGES_URL, headers=headers, json=payload)

        if response.status_code == 200:
            return {"working": True, "status": "ok", "message": "Claude API is working"}

        if response.status_code == 401:
            return {"working": False, "status": "invalid_key", "message": "Claude API key is invalid"}

        if response.status_code == 429:
            error_type, error_message, body_text = _error_payload(response)
            if error_type == "credit_limit_error" or "credit" in error_message.lower() or "credit" in body_text.lower():
                return {
                    "working": False,
                    "status": "credits_exhausted",
                    "message": "Your Claude API credits are exhausted. Top up at console.anthropic.com"
                }
            return {
                "working": True,
                "status": "rate_limited",
                "message": "Claude is rate limited - try again in a moment"
            }

        if response.status_code >= 500:
            return {
                "working": True,
                "status": "anthropic_outage",
                "message": "Anthropic is experiencing issues - not your fault"
            }

        _, error_message, _ = _error_payload(response)
        return {
            "working": False,
            "status": "unknown_error",
            "message": error_message or f"Claude check failed with status {response.status_code}"
        }
    except httpx.TimeoutException:
        return {
            "working": True,
            "status": "timeout",
            "message": "Claude check timed out - may be a network issue"
        }
    except Exception as exc:
        return {"working": False, "status": "unknown_error", "message": str(exc)}


async def check_claude_key_status(claude_api_key: str, user_id: UUID | str | None = None) -> dict[str, Any]:
    key = _cache_key(claude_api_key, user_id)
    cached = _cached_result(key)
    if cached:
        return cached

    lock = _LOCKS.setdefault(key, asyncio.Lock())
    async with lock:
        cached = _cached_result(key)
        if cached:
            return cached

        result = await _probe_claude_key(claude_api_key)
        return _store_result(key, result)
