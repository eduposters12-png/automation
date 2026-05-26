import hashlib
import time
import uuid
from typing import Any

import httpx

from backend.app.core.config import get_settings

OPENAI_IMAGE_URL = "https://api.openai.com/v1/images/generations"
OPENAI_IMAGE_MODEL = "gpt-image-1"
STANDARD_SIZE = "1024x1024"
HIGH_RES_SIZE = "1536x1024"
SUPPORTED_IMAGE_SIZES = {"1024x1024", "1024x1536", "1536x1024"}


class ImageGenerationError(Exception):
    pass


class CloudinaryUploadError(Exception):
    pass


def build_image_prompt(product_idea: dict[str, Any], shop_style: str, is_high_res: bool) -> str:
    title = product_idea.get("title") or product_idea.get("productTitle") or "Etsy product"
    description = product_idea.get("descriptionIdea") or product_idea.get("description") or ""
    keywords = product_idea.get("targetKeywords") or product_idea.get("keywords") or []
    keyword_text = ", ".join(str(keyword) for keyword in keywords if keyword)
    style_text = shop_style.strip() if shop_style else "clean, modern, conversion-focused"

    prompt_parts = [
        f"Create a clean product mockup for an Etsy listing titled: {title}.",
        "Use a white or soft neutral background, balanced natural lighting, and a professional marketplace composition.",
        "The image should look like polished Etsy listing photography, not a banner, poster, or ad.",
        f"Visual style notes: {style_text}.",
    ]
    if description:
        prompt_parts.append(f"Product concept: {description}.")
    if keyword_text:
        prompt_parts.append(f"Target buyer search keywords to visually support: {keyword_text}.")
    if is_high_res:
        prompt_parts.append("Ultra detailed, 4K quality, professional product photography.")

    return " ".join(prompt_parts)


def _image_size(is_high_res: bool, requested_size: str | None = None) -> str:
    if requested_size in SUPPORTED_IMAGE_SIZES:
        return requested_size
    return HIGH_RES_SIZE if is_high_res else STANDARD_SIZE


async def generate_product_image(prompt: str, is_high_res: bool, image_size: str | None = None) -> str:
    settings = get_settings()
    if not settings.openai_api_key:
        raise ImageGenerationError("OPENAI_API_KEY is not configured")

    headers = {
        "Authorization": f"Bearer {settings.openai_api_key}",
        "Content-Type": "application/json"
    }
    payload = {
        "model": OPENAI_IMAGE_MODEL,
        "prompt": prompt,
        "size": _image_size(is_high_res, image_size),
        "quality": "high" if is_high_res else "medium",
        "n": 1
    }

    async with httpx.AsyncClient(timeout=120) as client:
        try:
            response = await client.post(OPENAI_IMAGE_URL, headers=headers, json=payload)
        except httpx.HTTPError as exc:
            raise ImageGenerationError("OpenAI image request failed") from exc

    if response.status_code >= 400:
        raise ImageGenerationError("OpenAI image request failed")

    try:
        data = response.json()
        image_data = data["data"][0]["b64_json"]
    except (KeyError, IndexError, TypeError, ValueError) as exc:
        raise ImageGenerationError("OpenAI returned invalid image data") from exc

    if not image_data:
        raise ImageGenerationError("OpenAI returned empty image data")
    return image_data


def _cloudinary_signature(params: dict[str, str], api_secret: str) -> str:
    payload = "&".join(f"{key}={params[key]}" for key in sorted(params))
    return hashlib.sha1(f"{payload}{api_secret}".encode("utf-8")).hexdigest()


async def upload_to_cloudinary(base64_data: str, listing_id: str) -> str:
    settings = get_settings()
    if not settings.cloudinary_cloud_name or not settings.cloudinary_api_key or not settings.cloudinary_api_secret:
        raise CloudinaryUploadError("Cloudinary is not configured")

    timestamp = str(int(time.time()))
    public_id = f"listifyai/listings/{listing_id}/{uuid.uuid4().hex}"
    params_to_sign = {"public_id": public_id, "timestamp": timestamp}
    signature = _cloudinary_signature(params_to_sign, settings.cloudinary_api_secret)
    upload_url = f"https://api.cloudinary.com/v1_1/{settings.cloudinary_cloud_name}/image/upload"
    data = {
        "file": f"data:image/png;base64,{base64_data}",
        "api_key": settings.cloudinary_api_key,
        "timestamp": timestamp,
        "public_id": public_id,
        "signature": signature
    }

    async with httpx.AsyncClient(timeout=60) as client:
        try:
            response = await client.post(upload_url, data=data)
        except httpx.HTTPError as exc:
            raise CloudinaryUploadError("Cloudinary upload failed") from exc

    if response.status_code >= 400:
        raise CloudinaryUploadError("Cloudinary upload failed")

    try:
        payload = response.json()
    except ValueError as exc:
        raise CloudinaryUploadError("Cloudinary returned invalid JSON") from exc

    secure_url = payload.get("secure_url")
    if not secure_url:
        raise CloudinaryUploadError("Cloudinary returned no secure URL")
    return str(secure_url)
