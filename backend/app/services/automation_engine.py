import asyncio
import json
import logging
import uuid
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
from typing import Any

import httpx
from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.app.core.security import decrypt_secret
from backend.app.db.session import SessionLocal
from backend.app.models.automation_config import (
    AutoLogEvent,
    AutoMode,
    AutomationConfig,
    AutomationLog,
    QualityMode
)
from backend.app.models.listing import Listing, ListingStatus
from backend.app.models.notification import Notification, NotificationType
from backend.app.models.shop import Shop
from backend.app.services import credit_calculator, credit_service, multi_page_service
from backend.app.services.claude_service import ANTHROPIC_MESSAGES_URL, ANTHROPIC_VERSION, CLAUDE_MODEL
from backend.app.services.copy_service import generate_listing_copy
from backend.app.services.queue_service import enqueue_upload_job
from backend.app.services.video_service import generate_listing_video, upload_video

logger = logging.getLogger(__name__)

FAST_COST = credit_calculator.cost_per_listing("FAST")
MAX_TOPIC_DISCOVERY = 5


def _enum_value(value: Any) -> str:
    return getattr(value, "value", str(value))


def _topic_id(topic: dict[str, Any]) -> str:
    existing = topic.get("id")
    if existing:
        return str(existing)
    topic["id"] = uuid.uuid4().hex
    return str(topic["id"])


def normalise_topic(topic: dict[str, Any], status: str = "pending") -> dict[str, Any]:
    entry = {
        "id": str(topic.get("id") or uuid.uuid4().hex),
        "topic": str(topic.get("topic") or "").strip(),
        "description": str(topic.get("description") or "").strip(),
        "status": str(topic.get("status") or status)
    }
    if topic.get("listing_id"):
        entry["listing_id"] = str(topic["listing_id"])
    return entry


def _topics(config: AutomationConfig) -> list[dict[str, Any]]:
    topics = []
    for topic in config.topics_json or []:
        if isinstance(topic, dict):
            normalised = normalise_topic(topic, str(topic.get("status") or "pending"))
            if normalised["topic"]:
                topics.append(normalised)
    config.topics_json = topics
    return topics


def append_user_topics(config: AutomationConfig, topics: list[dict[str, Any]]) -> None:
    current = _topics(config)
    for topic in topics:
        normalised = normalise_topic(topic)
        if normalised["topic"]:
            current.append(normalised)
    config.topics_json = current


def remove_topic(config: AutomationConfig, topic_id: str) -> bool:
    current = _topics(config)
    next_topics = [topic for topic in current if _topic_id(topic) != topic_id]
    removed = len(next_topics) != len(current)
    config.topics_json = next_topics
    return removed


def _log(db: Session, shop_id: uuid.UUID, event_type: AutoLogEvent, message: str, metadata: dict | None = None) -> None:
    db.add(AutomationLog(
        shop_id=shop_id,
        event_type=event_type,
        message=message,
        metadata_json=metadata or {}
    ))


def send_notification(
    db: Session,
    user_id: uuid.UUID,
    type: NotificationType,
    title: str,
    message: str,
    metadata: dict | None = None,
    action_url: str | None = None
) -> None:
    db.add(Notification(
        user_id=user_id,
        type=type,
        title=title,
        message=message,
        action_url=action_url,
        metadata_json=metadata or {}
    ))
    db.commit()
    # TODO: Add email sending here using SendGrid or SMTP.


async def _call_claude(prompt: str, claude_api_key: str) -> str:
    headers = {
        "x-api-key": claude_api_key,
        "anthropic-version": ANTHROPIC_VERSION,
        "Content-Type": "application/json"
    }
    body = {
        "model": CLAUDE_MODEL,
        "max_tokens": 3000,
        "temperature": 0.25,
        "messages": [{"role": "user", "content": prompt}]
    }
    async with httpx.AsyncClient(timeout=60) as client:
        response = await client.post(ANTHROPIC_MESSAGES_URL, headers=headers, json=body)
    response.raise_for_status()
    payload = response.json()
    text = "".join(
        block.get("text", "")
        for block in payload.get("content", [])
        if isinstance(block, dict) and block.get("type") == "text"
    ).strip()
    return text


async def discover_topics_from_etsy(shop: Shop, db: Session, count: int = MAX_TOPIC_DISCOVERY) -> list[dict]:
    analysis = shop.analysis_json if isinstance(shop.analysis_json, dict) else {}
    if not shop.claude_api_key_encrypted:
        return []
    claude_api_key = decrypt_secret(shop.claude_api_key_encrypted)
    prompt = f"""You are an Etsy product research expert.

Shop niche: {analysis.get('niche')}
Shop style: {analysis.get('style')}
Existing top sellers: {analysis.get('strengths')}

Find {count} NEW trending product topics for this shop that are:
- Currently trending on Etsy in 2026
- Match the shop's niche and style
- Have high search volume but moderate competition
- Can be made as printable/digital products

For each topic provide a brief description so the AI image generator understands exactly what to create.

Respond ONLY in valid JSON:
[
  {{
    "topic": "short topic name",
    "description": "2-3 sentence description of exactly what images to create, style, colors, content"
  }}
]
"""
    try:
        text = await _call_claude(prompt, claude_api_key)
        parsed = json.loads(text)
    except Exception:
        logger.exception("Could not discover automation topics for shop %s", shop.id)
        _log(db, shop.id, AutoLogEvent.ERROR, "Could not discover automation topics.", {"source": "topic_discovery"})
        db.commit()
        return []
    if not isinstance(parsed, list):
        return []
    return [
        {"topic": str(item.get("topic") or "").strip(), "description": str(item.get("description") or "").strip()}
        for item in parsed
        if isinstance(item, dict) and str(item.get("topic") or "").strip()
    ][:count]


def _reset_daily_count_if_needed(config: AutomationConfig) -> None:
    today = datetime.now(timezone.utc).date()
    if config.today_date != today:
        config.today_date = today
        config.listings_created_today = 0


def _select_topic(config: AutomationConfig) -> dict[str, Any] | None:
    topics = _topics(config)
    topic = next((item for item in topics if item.get("status") == "in_progress"), None)
    if topic:
        return topic
    return next((item for item in topics if item.get("status") == "pending"), None)


def _set_topic_status(config: AutomationConfig, topic_id: str, status: str, listing_id: uuid.UUID | None = None) -> None:
    topics = _topics(config)
    for topic in topics:
        if _topic_id(topic) == topic_id:
            topic["status"] = status
            if listing_id:
                topic["listing_id"] = str(listing_id)
            break
    config.topics_json = topics


def _max_pages_for_quality(quality: str) -> int | None:
    if quality == "BALANCED":
        return 8
    if quality == "FAST":
        return 4
    return None


def _shop_analysis(shop: Shop) -> dict[str, Any]:
    return shop.analysis_json if isinstance(shop.analysis_json, dict) else {}


def _copy_price(value: Any) -> Decimal | None:
    try:
        return Decimal(str(value))
    except (InvalidOperation, TypeError, ValueError):
        return None


async def _generate_copy(db: Session, shop: Shop, listing: Listing, topic: dict[str, Any]) -> None:
    if not shop.claude_api_key_encrypted:
        return
    product_idea = {
        "title": listing.title or topic["topic"],
        "description": listing.description or topic.get("description") or "",
        "tags": listing.tags or []
    }
    copy = await generate_listing_copy(product_idea, _shop_analysis(shop), decrypt_secret(shop.claude_api_key_encrypted))
    credit_service.deduct_credits(db, shop.user_id, "COPY_GENERATION", listing_id=listing.id)
    listing.title = str(copy["title"])[:140]
    listing.description = str(copy["description"])
    listing.tags = [str(tag).strip() for tag in copy["tags"] if str(tag).strip()][:13]
    listing.price = _copy_price(copy.get("suggestedPrice"))
    listing.status = ListingStatus.COPY_READY
    db.add(listing)
    db.commit()


async def _try_generate_full_video(db: Session, shop: Shop, listing: Listing, topic: dict[str, Any]) -> None:
    if not listing.image_urls:
        return
    action = "VIDEO_GENERATION"
    credit_service.deduct_credits(db, shop.user_id, action, listing_id=listing.id)
    try:
        video_bytes = await generate_listing_video(
            image_urls=list(listing.image_urls or []),
            product_idea={"title": listing.title or topic["topic"], "description": topic.get("description") or ""},
            shop_style=str((_shop_analysis(shop).get("style") or shop.niche or "clean Etsy product style"))
        )
        listing.video_url = await upload_video(video_bytes, str(listing.id))
        db.add(listing)
        db.commit()
    except Exception:
        logger.exception("Automation video generation failed for listing %s", listing.id)
        credit_service.refund_credits(db, shop.user_id, action, listing_id=listing.id, reason="automation_video_failed")


async def _queue_etsy_upload(db: Session, shop: Shop, listing: Listing) -> str:
    credit_service.deduct_credits(db, shop.user_id, "ETSY_LISTING_UPLOAD", listing_id=listing.id)
    listing.status = ListingStatus.QUEUED
    listing.error_message = None
    db.add(listing)
    db.commit()
    return await enqueue_upload_job(listing.id, shop.user_id, shop.id)


async def process_one_auto_listing(shop_id: str, db: Session) -> dict:
    config = db.scalar(select(AutomationConfig).where(AutomationConfig.shop_id == uuid.UUID(shop_id)))
    shop = db.get(Shop, uuid.UUID(shop_id))
    if not config or not shop:
        return {"success": False, "reason": "missing_config"}

    try:
        credit_status = credit_service.get_credit_status(db, shop.user_id)
        balance = int(credit_status["software_credits"]["balance"])
        if balance < FAST_COST:
            config.is_running = False
            _log(db, shop.id, AutoLogEvent.CREDITS_EXHAUSTED, "Automation stopped because credits are exhausted.", {"balance": balance})
            send_notification(db, shop.user_id, NotificationType.CREDITS_EXHAUSTED, "Credits exhausted", "Auto mode paused because your credit balance is too low.", {"balance": balance}, "/automation")
            db.commit()
            return {"success": False, "reason": "credits_exhausted"}

        quality = _enum_value(config.quality_mode)
        if config.auto_quality_adjust:
            adjustment = credit_calculator.get_auto_quality_adjustment(balance, quality)
            if adjustment["should_adjust"]:
                old_quality = quality
                config.quality_mode = QualityMode[adjustment["new_quality"]]
                _log(db, shop.id, AutoLogEvent.QUALITY_ADJUSTED, f"Quality adjusted from {old_quality} to {adjustment['new_quality']}.", adjustment)
                if config.mode == AutoMode.HYBRID:
                    send_notification(
                        db,
                        shop.user_id,
                        NotificationType.QUALITY_ADJUSTED,
                        "Quality adjusted",
                        f"Automation changed quality from {old_quality} to {adjustment['new_quality']} to stretch credits.",
                        adjustment,
                        "/automation"
                    )
                db.commit()
                quality = adjustment["new_quality"]

        _reset_daily_count_if_needed(config)
        if config.listings_created_today >= config.daily_limit:
            _log(db, shop.id, AutoLogEvent.DAILY_LIMIT_REACHED, "Daily automation limit reached.", {"daily_limit": config.daily_limit})
            if config.mode == AutoMode.HYBRID:
                send_notification(db, shop.user_id, NotificationType.DAILY_LIMIT_REACHED, "Daily limit reached", "Auto mode has reached today's listing limit.", {"daily_limit": config.daily_limit}, "/automation")
            db.commit()
            return {"success": False, "reason": "daily_limit_reached"}

        topic = _select_topic(config)
        if not topic:
            discovered = await discover_topics_from_etsy(shop, db, count=MAX_TOPIC_DISCOVERY)
            if discovered:
                append_user_topics(config, discovered)
                _log(db, shop.id, AutoLogEvent.TOPIC_AUTO_DISCOVERED, f"Claude discovered {len(discovered)} new automation topics.", {"count": len(discovered)})
                if config.mode == AutoMode.HYBRID:
                    send_notification(db, shop.user_id, NotificationType.AUTO_TOPIC_DISCOVERED, "New topics discovered", f"Claude added {len(discovered)} new topics to your automation list.", {"count": len(discovered)}, "/automation")
                db.commit()
            topic = _select_topic(config)
        if not topic:
            config.is_running = False
            _log(db, shop.id, AutoLogEvent.TOPIC_EXHAUSTED, "Automation stopped because no topics are available.")
            if config.mode == AutoMode.HYBRID:
                send_notification(db, shop.user_id, NotificationType.TOPIC_EXHAUSTED, "No topics available", "Claude could not discover new topics. Auto mode has paused.", {}, "/automation")
            db.commit()
            return {"success": False, "reason": "no_topics"}

        topic_id = _topic_id(topic)
        _set_topic_status(config, topic_id, "in_progress")
        db.commit()

        listing = None
        if topic.get("listing_id"):
            try:
                listing = db.get(Listing, uuid.UUID(str(topic["listing_id"])))
            except ValueError:
                listing = None
        if listing is None:
            listing = Listing(
                shop_id=shop.id,
                is_multi_page=True,
                is_bundle=True,
                title=str(topic["topic"])[:140],
                description=str(topic.get("description") or ""),
                status=ListingStatus.DRAFT,
                image_urls=[],
                tags=[],
                page_images_json=[]
            )
            db.add(listing)
            db.commit()
            db.refresh(listing)
            _set_topic_status(config, topic_id, "in_progress", listing.id)
            db.commit()

        if not listing.pdf_url:
            result = await multi_page_service.run_multi_page_generation(str(listing.id), db, max_pages=_max_pages_for_quality(quality))
            if not result.get("success"):
                raise RuntimeError("Multi-page generation failed")
            db.refresh(listing)

        if not listing.description or not listing.tags:
            await _generate_copy(db, shop, listing, topic)
            db.refresh(listing)

        if quality == "FULL" and not listing.video_url:
            await _try_generate_full_video(db, shop, listing, topic)
            db.refresh(listing)

        job_id = await _queue_etsy_upload(db, shop, listing)
        _set_topic_status(config, topic_id, "done", listing.id)
        config.listings_created_today += 1
        config.listings_created_total += 1
        config.last_run_at = datetime.now(timezone.utc)
        _log(db, shop.id, AutoLogEvent.LISTING_CREATED, f"Created listing for {topic['topic']}.", {"listing_id": str(listing.id), "topic": topic["topic"], "job_id": job_id})
        if config.mode == AutoMode.HYBRID:
            send_notification(db, shop.user_id, NotificationType.LISTING_CREATED, "Listing created", f"Created and queued Etsy upload for {topic['topic']}.", {"listing_id": str(listing.id), "topic_id": topic_id}, f"/new-listing/package?listing_id={listing.id}")
        db.commit()
        return {"success": True, "listing_id": str(listing.id), "topic": topic["topic"]}
    except Exception as exc:
        db.rollback()
        config = db.scalar(select(AutomationConfig).where(AutomationConfig.shop_id == uuid.UUID(shop_id)))
        shop = db.get(Shop, uuid.UUID(shop_id))
        if config and shop:
            topic = _select_topic(config)
            if topic:
                _set_topic_status(config, _topic_id(topic), "pending")
            _log(db, shop.id, AutoLogEvent.ERROR, str(exc)[:1000], {"error": str(exc)})
            db.commit()
        return {"success": False, "reason": "error", "error": str(exc)}


async def run_auto_cycle(shop_id: str, db: Session) -> dict:
    config = db.scalar(select(AutomationConfig).where(AutomationConfig.shop_id == uuid.UUID(shop_id)))
    if not config or not config.is_running or config.mode not in {AutoMode.AUTO, AutoMode.HYBRID}:
        return {"processed": 0, "results": []}

    results = []
    while True:
        result = await process_one_auto_listing(shop_id, db)
        results.append(result)
        if not result.get("success"):
            break
        db.refresh(config)
        if not config.is_running:
            break
        await asyncio.sleep(30)
    return {"processed": len(results), "results": results}


async def run_auto_cycle_background(shop_id: str) -> dict:
    db = SessionLocal()
    try:
        return await run_auto_cycle(shop_id, db)
    finally:
        db.close()
