import json
from typing import Any

import httpx

ANTHROPIC_MESSAGES_URL = "https://api.anthropic.com/v1/messages"
CLAUDE_MODEL = "claude-sonnet-4-5"
ANTHROPIC_VERSION = "2023-06-01"

CLAUDE_PROMPT_TEMPLATE = """You are an expert Etsy marketplace analyst with deep knowledge of trends, buyer psychology, and digital product strategies.

Analyze the following Etsy shop data and current market trends carefully.

Shop Data:
__SHOP_DATA__

Current Market Trends:
__TRENDS__

Respond ONLY in valid JSON with this exact structure, no extra text:
{
  "niche": "string",
  "style": "string",
  "strengths": ["string", "string", "string", "string", "string"],
  "opportunities": [
    { "title": "string", "description": "string" },
    { "title": "string", "description": "string" },
    { "title": "string", "description": "string" }
  ],
  "productIdeas": [
    {
      "title": "string",
      "descriptionIdea": "string",
      "targetKeywords": ["string", "string", "string"],
      "suggestedPrice": number,
      "potential": "High" | "Medium" | "Low",
      "rationale": "string"
    }
  ]
}
Return exactly 3 opportunities and exactly 10 productIdeas.
"""


class ClaudeAnalysisError(Exception):
    pass


class ClaudeJSONParseError(Exception):
    pass


def _build_prompt(shop_data: dict[str, Any], trends: list[str]) -> str:
    return (
        CLAUDE_PROMPT_TEMPLATE
        .replace("__SHOP_DATA__", json.dumps(shop_data, ensure_ascii=False, default=str, indent=2))
        .replace("__TRENDS__", json.dumps(trends, ensure_ascii=False, indent=2))
    )


async def _call_claude(prompt: str, claude_api_key: str) -> str:
    headers = {
        "x-api-key": claude_api_key,
        "anthropic-version": ANTHROPIC_VERSION,
        "Content-Type": "application/json"
    }
    body = {
        "model": CLAUDE_MODEL,
        "max_tokens": 6000,
        "temperature": 0.2,
        "messages": [{"role": "user", "content": prompt}]
    }

    async with httpx.AsyncClient(timeout=60) as client:
        try:
            response = await client.post(ANTHROPIC_MESSAGES_URL, headers=headers, json=body)
        except httpx.HTTPError as exc:
            raise ClaudeAnalysisError("Claude API request failed") from exc
        if response.status_code >= 400:
            raise ClaudeAnalysisError("Claude API request failed")
        try:
            payload = response.json()
        except ValueError as exc:
            raise ClaudeAnalysisError("Claude returned invalid JSON") from exc

    text_parts = [
        block.get("text", "")
        for block in payload.get("content", [])
        if isinstance(block, dict) and block.get("type") == "text"
    ]
    text = "".join(text_parts).strip()
    if not text:
        raise ClaudeAnalysisError("Claude returned an empty response")
    return text


def _validate_analysis(value: Any) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise ClaudeJSONParseError("Claude response was not a JSON object")
    if len(value.get("strengths") or []) != 5:
        raise ClaudeJSONParseError("Claude response must include exactly 5 strengths")
    if len(value.get("opportunities") or []) != 3:
        raise ClaudeJSONParseError("Claude response must include exactly 3 opportunities")
    if len(value.get("productIdeas") or []) != 10:
        raise ClaudeJSONParseError("Claude response must include exactly 10 productIdeas")
    return value


def _parse_analysis(text: str) -> dict[str, Any]:
    try:
        return _validate_analysis(json.loads(text))
    except json.JSONDecodeError as exc:
        raise ClaudeJSONParseError("Claude response was not valid JSON") from exc


async def analyze_shop(shop_data: dict[str, Any], trends: list[str], claude_api_key: str) -> dict[str, Any]:
    prompt = _build_prompt(shop_data, trends)
    first_response = await _call_claude(prompt, claude_api_key)
    try:
        return _parse_analysis(first_response)
    except ClaudeJSONParseError:
        retry_prompt = (
            f"{prompt}\n\n"
            "Your previous response was not valid parseable JSON. Return only one JSON object, "
            "with double-quoted keys and strings, no markdown fences, no comments, and no prose."
        )
        retry_response = await _call_claude(retry_prompt, claude_api_key)
        return _parse_analysis(retry_response)
