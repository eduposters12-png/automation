import json
from typing import Any

import httpx

from backend.app.services.image_service import HIGH_RES_SIZE, STANDARD_SIZE, SUPPORTED_IMAGE_SIZES

ANTHROPIC_MESSAGES_URL = "https://api.anthropic.com/v1/messages"
CLAUDE_MODEL = "claude-sonnet-4-5"
ANTHROPIC_VERSION = "2023-06-01"


async def _call_claude(prompt: str, claude_api_key: str, max_tokens: int = 1400) -> str:
    headers = {
        "x-api-key": claude_api_key,
        "anthropic-version": ANTHROPIC_VERSION,
        "Content-Type": "application/json"
    }
    body = {
        "model": CLAUDE_MODEL,
        "max_tokens": max_tokens,
        "temperature": 0.2,
        "messages": [{"role": "user", "content": prompt}]
    }
    async with httpx.AsyncClient(timeout=45) as client:
        response = await client.post(ANTHROPIC_MESSAGES_URL, headers=headers, json=body)
        response.raise_for_status()
        payload = response.json()

    text_parts = [
        block.get("text", "")
        for block in payload.get("content", [])
        if isinstance(block, dict) and block.get("type") == "text"
    ]
    return "".join(text_parts).strip()


def _product_title(product_idea: dict[str, Any]) -> str:
    return str(product_idea.get("title") or product_idea.get("productTitle") or "Etsy product")


def _keywords(product_idea: dict[str, Any]) -> list[str]:
    raw_keywords = product_idea.get("targetKeywords") or product_idea.get("keywords") or []
    if not isinstance(raw_keywords, list):
        return []
    return [str(keyword) for keyword in raw_keywords if keyword]


def _fallback_review(image_prompt: str) -> dict[str, Any]:
    return {
        "approved": False,
        "feedback": "Review unavailable",
        "improvedPrompt": image_prompt
    }


def _parse_json_object(text: str) -> dict[str, Any]:
    return json.loads(text)


async def choose_image_prompt_and_size(
    image_prompt: str,
    product_idea: dict[str, Any],
    shop_style: str,
    is_high_res: bool,
    claude_api_key: str
) -> dict[str, str]:
    fallback_size = HIGH_RES_SIZE if is_high_res else STANDARD_SIZE
    prompt = f"""You are an Etsy product photography director.

Improve this image generation prompt only if it will make the result more high-converting for Etsy.

Prompt:
"{image_prompt}"

Product: {_product_title(product_idea)}
Target keywords: {", ".join(_keywords(product_idea))}
Shop style notes: {shop_style}
High resolution requested: {is_high_res}

Choose the best image layout size for this product from exactly these values:
1024x1024, 1024x1536, 1536x1024

Respond ONLY in valid JSON:
{{
  "prompt": "string",
  "size": "1024x1024" | "1024x1536" | "1536x1024"
}}
"""
    try:
        text = await _call_claude(prompt, claude_api_key)
        payload = _parse_json_object(text)
        refined_prompt = str(payload.get("prompt") or image_prompt)
        size = str(payload.get("size") or fallback_size)
        if size not in SUPPORTED_IMAGE_SIZES:
            size = fallback_size
        return {"prompt": refined_prompt, "size": size}
    except Exception:
        return {"prompt": image_prompt, "size": fallback_size}


async def review_image(image_prompt: str, product_idea: dict[str, Any], claude_api_key: str) -> dict[str, Any]:
    prompt = f"""You are an Etsy product listing expert.
A product image was generated using this prompt:
"{image_prompt}"

The product is: {_product_title(product_idea)}
Target keywords: {", ".join(_keywords(product_idea))}

Review if this prompt would produce a professional, high-converting Etsy listing image.
Respond ONLY in valid JSON:
{{
  "approved": boolean,
  "feedback": "string (1-2 sentences)",
  "improvedPrompt": "string (improved image generation prompt)"
}}
"""
    try:
        text = await _call_claude(prompt, claude_api_key)
        payload = _parse_json_object(text)
        return {
            "approved": bool(payload.get("approved")),
            "feedback": str(payload.get("feedback") or "Review unavailable"),
            "improvedPrompt": str(payload.get("improvedPrompt") or image_prompt)
        }
    except Exception:
        return _fallback_review(image_prompt)
