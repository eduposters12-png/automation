import base64
import hashlib
import json
import logging
import time
from io import BytesIO
from typing import Any
from uuid import UUID

import httpx
from sqlalchemy.orm import Session

from backend.app.core.config import get_settings
from backend.app.core.security import decrypt_secret
from backend.app.models.listing import Listing, ListingStatus
from backend.app.models.shop import Shop
from backend.app.services import credit_service
from backend.app.services.claude_service import ANTHROPIC_MESSAGES_URL, ANTHROPIC_VERSION, CLAUDE_MODEL
from backend.app.services.image_service import generate_product_image

logger = logging.getLogger(__name__)

CLAUDE_PAGE_PLAN_PROMPT = """You are an expert Etsy digital product designer. Your goal is to plan a multi-page digital product that will sell well on Etsy.

Product Idea: {product_idea_json}
Shop Niche and Style: {shop_niche}, {shop_style}
{max_pages_hint}

Decide the OPTIMAL number of pages for this product. Consider:
- More pages = more value for buyer, but more AI generation cost
- Fewer pages = faster to generate, lower cost, but less perceived value
- Aim for the minimum pages that still make the product feel complete and worth buying
- Most Etsy digital products succeed with 10-30 pages
- Only go above 30 if the topic genuinely requires it (e.g. full alphabet = 26 pages)

For each page, write a specific, detailed image generation prompt that will create a professional, printable poster/page.

Respond ONLY in valid JSON with no extra text:
{
  "total_pages": number,
  "product_title": "string (max 140 chars, SEO optimized for Etsy)",
  "reasoning": "string (1-2 sentences explaining why this many pages)",
  "pages": [
    {
      "page_number": number,
      "page_title": "string (short, what this page covers)",
      "image_prompt": "string (detailed prompt for GPT image generation, include: style, colors, layout, text to show, background)",
      "print_size": "A4" | "Letter" | "Square"
    }
  ]
}
"""


class MultiPageGenerationError(Exception):
    pass


def _load_pdf_dependencies():
    try:
        from PIL import Image
        from reportlab.lib.utils import ImageReader
        from reportlab.pdfgen import canvas
    except ImportError as exc:
        raise MultiPageGenerationError("PDF generation dependencies are not installed") from exc
    return Image, ImageReader, canvas


def _cloudinary_signature(params: dict[str, str], api_secret: str) -> str:
    payload = "&".join(f"{key}={params[key]}" for key in sorted(params))
    return hashlib.sha1(f"{payload}{api_secret}".encode("utf-8")).hexdigest()


async def _call_claude(prompt: str, claude_api_key: str) -> str:
    headers = {
        "x-api-key": claude_api_key,
        "anthropic-version": ANTHROPIC_VERSION,
        "Content-Type": "application/json"
    }
    body = {
        "model": CLAUDE_MODEL,
        "max_tokens": 2000,
        "temperature": 0.2,
        "messages": [{"role": "user", "content": prompt}]
    }

    async with httpx.AsyncClient(timeout=60) as client:
        try:
            response = await client.post(ANTHROPIC_MESSAGES_URL, headers=headers, json=body)
        except httpx.HTTPError as exc:
            raise MultiPageGenerationError("Claude page planning request failed") from exc
    if response.status_code >= 400:
        raise MultiPageGenerationError("Claude page planning request failed")

    try:
        payload = response.json()
    except ValueError as exc:
        raise MultiPageGenerationError("Claude returned invalid JSON") from exc

    text_parts = [
        block.get("text", "")
        for block in payload.get("content", [])
        if isinstance(block, dict) and block.get("type") == "text"
    ]
    text = "".join(text_parts).strip()
    if not text:
        raise MultiPageGenerationError("Claude returned an empty page plan")
    return text


def _parse_page_plan(text: str) -> dict[str, Any]:
    try:
        plan = json.loads(text)
    except json.JSONDecodeError as exc:
        raise MultiPageGenerationError("Claude page plan was not valid JSON") from exc

    pages = plan.get("pages") if isinstance(plan, dict) else None
    total_pages = plan.get("total_pages") if isinstance(plan, dict) else None
    if not isinstance(pages, list) or not pages or not isinstance(total_pages, int):
        raise MultiPageGenerationError("Claude page plan was missing required fields")
    return plan


def _cap_page_plan(plan: dict[str, Any], max_pages: int | None) -> dict[str, Any]:
    if max_pages is None:
        return plan
    pages = plan.get("pages")
    if isinstance(pages, list) and len(pages) > max_pages:
        plan["pages"] = pages[:max_pages]
    if int(plan.get("total_pages") or 0) > max_pages:
        plan["total_pages"] = max_pages
    return plan


async def plan_product_pages(product_idea: dict, shop_analysis: dict, claude_api_key: str, max_pages: int | None = None) -> dict:
    shop_niche = str(shop_analysis.get("niche") or "Etsy digital products")
    shop_style = str(shop_analysis.get("style") or "clean printable design")
    max_pages_hint = f"Maximum pages allowed: {max_pages}. Do not exceed this." if max_pages is not None else ""
    prompt = (
        CLAUDE_PAGE_PLAN_PROMPT
        .replace("{product_idea_json}", json.dumps(product_idea, ensure_ascii=False, default=str))
        .replace("{shop_niche}", shop_niche)
        .replace("{shop_style}", shop_style)
        .replace("{max_pages_hint}", max_pages_hint)
    )

    first_response = await _call_claude(prompt, claude_api_key)
    try:
        return _cap_page_plan(_parse_page_plan(first_response), max_pages)
    except MultiPageGenerationError:
        retry_prompt = (
            f"{prompt}\n\n"
            "Your previous response was not valid parseable JSON. Return only one JSON object, "
            "with double-quoted keys and strings, no markdown fences, no comments, and no prose."
        )
        retry_response = await _call_claude(retry_prompt, claude_api_key)
        return _cap_page_plan(_parse_page_plan(retry_response), max_pages)


async def _upload_image_to_cloudinary(image_data: str, public_id: str) -> str:
    settings = get_settings()
    if not settings.cloudinary_cloud_name or not settings.cloudinary_api_key or not settings.cloudinary_api_secret:
        raise MultiPageGenerationError("Cloudinary is not configured")

    timestamp = str(int(time.time()))
    params_to_sign = {"public_id": public_id, "timestamp": timestamp}
    signature = _cloudinary_signature(params_to_sign, settings.cloudinary_api_secret)
    upload_url = f"https://api.cloudinary.com/v1_1/{settings.cloudinary_cloud_name}/image/upload"
    data = {
        "file": f"data:image/png;base64,{image_data}",
        "api_key": settings.cloudinary_api_key,
        "timestamp": timestamp,
        "public_id": public_id,
        "signature": signature
    }

    async with httpx.AsyncClient(timeout=60) as client:
        try:
            response = await client.post(upload_url, data=data)
        except httpx.HTTPError as exc:
            raise MultiPageGenerationError("Cloudinary image upload failed") from exc
    if response.status_code >= 400:
        raise MultiPageGenerationError("Cloudinary image upload failed")

    secure_url = response.json().get("secure_url")
    if not secure_url:
        raise MultiPageGenerationError("Cloudinary returned no image URL")
    return str(secure_url)


async def generate_page_image(prompt: str, page_number: int, listing_id: str, print_size: str) -> str:
    image_size = "1024x1024" if print_size == "Square" else "1024x1536"
    image_data = await generate_product_image(prompt, is_high_res=False, image_size=image_size)
    public_id = f"listify/multi_page/{listing_id}/page_{page_number:03d}"
    return await _upload_image_to_cloudinary(image_data, public_id)


async def compile_pdf(page_image_urls: list[str], listing_id: str) -> bytes:
    Image, ImageReader, canvas = _load_pdf_dependencies()
    buffer = BytesIO()
    pdf = canvas.Canvas(buffer)
    rendered_pages = 0

    async with httpx.AsyncClient(timeout=60, follow_redirects=True) as client:
        for page_index, image_url in enumerate(page_image_urls, start=1):
            try:
                response = await client.get(image_url)
                response.raise_for_status()
                image_bytes = response.content
                image = Image.open(BytesIO(image_bytes))
                image.load()
            except Exception:
                logger.exception("Could not download multi-page image %s for listing %s", page_index, listing_id)
                continue

            width_px, height_px = image.size
            page_width = 595
            page_height = 842
            if width_px > 0 and height_px > 0:
                aspect = width_px / height_px
                if abs(aspect - (page_width / page_height)) > 0.2:
                    page_height = page_width / aspect

            pdf.setPageSize((page_width, page_height))
            image_reader = ImageReader(BytesIO(image_bytes))
            scale = max(page_width / width_px, page_height / height_px)
            draw_width = width_px * scale
            draw_height = height_px * scale
            x = (page_width - draw_width) / 2
            y = (page_height - draw_height) / 2
            pdf.drawImage(image_reader, x, y, width=draw_width, height=draw_height, preserveAspectRatio=True)
            pdf.showPage()
            rendered_pages += 1

    if rendered_pages == 0:
        raise MultiPageGenerationError("No page images were available to compile into a PDF")

    pdf.save()
    return buffer.getvalue()


async def upload_pdf_to_cloudinary(pdf_bytes: bytes, listing_id: str) -> str:
    settings = get_settings()
    if not settings.cloudinary_cloud_name or not settings.cloudinary_api_key or not settings.cloudinary_api_secret:
        raise MultiPageGenerationError("Cloudinary is not configured")

    timestamp = str(int(time.time()))
    public_id = f"listify/pdfs/{listing_id}/product"
    params_to_sign = {"public_id": public_id, "timestamp": timestamp}
    signature = _cloudinary_signature(params_to_sign, settings.cloudinary_api_secret)
    upload_url = f"https://api.cloudinary.com/v1_1/{settings.cloudinary_cloud_name}/raw/upload"
    data = {
        "file": f"data:application/pdf;base64,{base64.b64encode(pdf_bytes).decode('utf-8')}",
        "api_key": settings.cloudinary_api_key,
        "timestamp": timestamp,
        "public_id": public_id,
        "signature": signature
    }

    async with httpx.AsyncClient(timeout=60) as client:
        try:
            response = await client.post(upload_url, data=data)
        except httpx.HTTPError as exc:
            raise MultiPageGenerationError("Cloudinary PDF upload failed") from exc
    if response.status_code >= 400:
        raise MultiPageGenerationError("Cloudinary PDF upload failed")

    secure_url = response.json().get("secure_url")
    if not secure_url:
        raise MultiPageGenerationError("Cloudinary returned no PDF URL")
    return str(secure_url)


async def run_multi_page_generation(listing_id: str, db: Session, max_pages: int | None = None) -> dict:
    listing_uuid = UUID(listing_id)
    listing = db.get(Listing, listing_uuid)
    if not listing or not listing.is_multi_page:
        raise MultiPageGenerationError("Multi-page listing not found")

    shop = db.get(Shop, listing.shop_id)
    if not shop:
        raise MultiPageGenerationError("Shop not found")

    shop_analysis = shop.analysis_json if isinstance(shop.analysis_json, dict) else {}
    product_idea = {
        "title": listing.title or "Etsy digital product",
        "description": listing.description or ""
    }
    claude_api_key = decrypt_secret(shop.claude_api_key_encrypted or "")

    try:
        plan = await plan_product_pages(product_idea, shop_analysis, claude_api_key, max_pages=max_pages)
    except Exception as exc:
        listing.status = ListingStatus.FAILED
        listing.error_message = str(exc)
        db.add(listing)
        db.commit()
        raise

    listing.page_plan_json = plan
    listing.total_pages_planned = int(plan["total_pages"])
    listing.pages_completed = 0
    listing.page_images_json = []
    if plan.get("product_title"):
        listing.title = str(plan["product_title"])[:140]
    db.add(listing)
    db.commit()

    image_urls: list[str] = []
    for page in plan["pages"]:
        page_number = int(page.get("page_number") or len(image_urls) + 1)
        prompt = str(page.get("image_prompt") or "")
        print_size = str(page.get("print_size") or "A4")
        if not prompt:
            logger.error("Skipping page %s for listing %s because the prompt is empty", page_number, listing_id)
            continue

        action = "IMAGE_GENERATION"
        try:
            credit_service.deduct_credits(db, shop.user_id, action, listing_id=listing.id)
        except Exception as exc:
            listing.status = ListingStatus.FAILED
            listing.error_message = str(exc)
            db.add(listing)
            db.commit()
            raise
        try:
            image_url = await generate_page_image(prompt, page_number, listing_id, print_size)
        except Exception:
            logger.exception("Page image generation failed for listing %s page %s", listing_id, page_number)
            credit_service.refund_credits(db, shop.user_id, action, listing_id=listing.id)
            continue

        image_urls.append(image_url)
        page_images = list(listing.page_images_json or [])
        page_images.append({
            "page_number": page_number,
            "prompt": prompt,
            "image_url": image_url,
            "approved": True
        })
        listing.page_images_json = page_images
        listing.image_urls = image_urls
        listing.primary_image_url = listing.primary_image_url or image_url
        listing.pages_completed = int(listing.pages_completed or 0) + 1
        db.add(listing)
        db.commit()

    try:
        pdf_bytes = await compile_pdf(image_urls, listing_id)
        pdf_url = await upload_pdf_to_cloudinary(pdf_bytes, listing_id)
    except Exception as exc:
        listing.status = ListingStatus.FAILED
        listing.error_message = str(exc)
        db.add(listing)
        db.commit()
        return {"success": False, "total_pages": listing.total_pages_planned or 0, "pdf_url": None}

    listing.pdf_url = pdf_url
    listing.status = ListingStatus.COPY_READY
    listing.error_message = None
    db.add(listing)
    db.commit()
    return {"success": True, "total_pages": listing.total_pages_planned or len(image_urls), "pdf_url": pdf_url}
