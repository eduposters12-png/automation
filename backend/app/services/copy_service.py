import json
from decimal import Decimal, InvalidOperation
from typing import Any

import httpx

ANTHROPIC_MESSAGES_URL = "https://api.anthropic.com/v1/messages"
CLAUDE_MODEL = "claude-sonnet-4-5"
ANTHROPIC_VERSION = "2023-06-01"

COPY_PROMPT_TEMPLATE = """You are an expert Etsy SEO copywriter. Write a complete listing for this product.

Product: __PRODUCT_IDEA__
Shop niche and style: __SHOP_NICHE__, __SHOP_STYLE__
Target keywords: __KEYWORDS__

Return ONLY valid JSON with no extra text:
{
  "title": "string (max 140 chars, keyword-rich, natural)",
  "description": "string (300-500 words, engaging, SEO optimized, uses line breaks)",
  "tags": ["string", ...] (exactly 13 tags, mix of broad and specific),
  "suggestedPrice": number
}
"""


class CopyGenerationError(Exception):
    pass


class CopyJSONParseError(Exception):
    pass


def _keywords(product_idea: dict[str, Any]) -> list[str]:
    keywords = product_idea.get("targetKeywords") or product_idea.get("keywords") or product_idea.get("tags") or []
    if not isinstance(keywords, list):
        return []
    return [str(keyword) for keyword in keywords if keyword][:13]


def _build_prompt(product_idea: dict[str, Any], shop_analysis: dict[str, Any]) -> str:
    return (
        COPY_PROMPT_TEMPLATE
        .replace("__PRODUCT_IDEA__", json.dumps(product_idea, ensure_ascii=False, default=str, indent=2))
        .replace("__SHOP_NICHE__", str(shop_analysis.get("niche") or "Etsy shop"))
        .replace("__SHOP_STYLE__", str(shop_analysis.get("style") or "clean Etsy listing style"))
        .replace("__KEYWORDS__", json.dumps(_keywords(product_idea), ensure_ascii=False))
    )


async def _call_claude(prompt: str, claude_api_key: str) -> str:
    headers = {
        "x-api-key": claude_api_key,
        "anthropic-version": ANTHROPIC_VERSION,
        "Content-Type": "application/json"
    }
    body = {
        "model": CLAUDE_MODEL,
        "max_tokens": 5000,
        "temperature": 0.3,
        "messages": [{"role": "user", "content": prompt}]
    }

    async with httpx.AsyncClient(timeout=60) as client:
        try:
            response = await client.post(ANTHROPIC_MESSAGES_URL, headers=headers, json=body)
        except httpx.HTTPError as exc:
            raise CopyGenerationError("Claude copy request failed") from exc
    if response.status_code >= 400:
        raise CopyGenerationError("Claude copy request failed")

    try:
        payload = response.json()
    except ValueError as exc:
        raise CopyGenerationError("Claude returned invalid JSON") from exc

    text_parts = [
        block.get("text", "")
        for block in payload.get("content", [])
        if isinstance(block, dict) and block.get("type") == "text"
    ]
    text = "".join(text_parts).strip()
    if not text:
        raise CopyGenerationError("Claude returned an empty response")
    return text


def _normalise_copy(value: Any) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise CopyJSONParseError("Claude copy was not a JSON object")

    title = str(value.get("title") or "").strip()
    description = str(value.get("description") or "").strip()
    tags = value.get("tags") or []
    if not isinstance(tags, list):
        raise CopyJSONParseError("Claude copy tags were invalid")
    tags = [str(tag).strip() for tag in tags if str(tag).strip()]

    try:
        suggested_price = Decimal(str(value.get("suggestedPrice")))
    except (InvalidOperation, ValueError, TypeError) as exc:
        raise CopyJSONParseError("Claude copy price was invalid") from exc

    if not title or not description or len(tags) != 13:
        raise CopyJSONParseError("Claude copy did not match the required shape")

    return {
        "title": title[:140],
        "description": description,
        "tags": tags[:13],
        "suggestedPrice": float(suggested_price)
    }


def _parse_copy(text: str) -> dict[str, Any]:
    try:
        return _normalise_copy(json.loads(text))
    except json.JSONDecodeError as exc:
        raise CopyJSONParseError("Claude copy was not valid JSON") from exc


async def generate_listing_copy(
    product_idea: dict[str, Any],
    shop_analysis: dict[str, Any],
    claude_api_key: str
) -> dict[str, Any]:
    prompt = _build_prompt(product_idea, shop_analysis)
    first_response = await _call_claude(prompt, claude_api_key)
    try:
        return _parse_copy(first_response)
    except CopyJSONParseError:
        retry_prompt = (
            f"{prompt}\n\n"
            "Your previous response was not valid parseable JSON. Return exactly one JSON object "
            "with double-quoted keys and strings, no markdown fences, no comments, and no prose."
        )
        retry_response = await _call_claude(retry_prompt, claude_api_key)
        return _parse_copy(retry_response)
