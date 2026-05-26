from __future__ import annotations

import asyncio
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Any
from uuid import UUID

from sqlalchemy.orm import Session

from backend.app.core.config import get_settings
from backend.app.db.session import SessionLocal
from backend.app.models.listing import Listing, ListingStatus
from backend.app.models.shop import Shop
from backend.app.services import credit_service
from backend.app.services.etsy_upload_service import EtsyUploadAuthError, full_upload_flow_with_refresh

try:
    from redis import Redis
    from rq import Queue
except ImportError:  # pragma: no cover - optional dependency path
    Redis = None
    Queue = None

QUEUE_NAME = "listing-upload"
MAX_RETRIES = 3


@dataclass
class InMemoryUploadJob:
    job_id: str
    listing_id: UUID
    user_id: UUID
    shop_id: UUID
    run_at: datetime
    attempts: int = 0
    last_error: str | None = None
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


_memory_jobs: list[InMemoryUploadJob] = []
_memory_worker_task: asyncio.Task[None] | None = None
_memory_lock = asyncio.Lock()


def _redis_queue() -> Queue | None:
    settings = get_settings()
    if not settings.redis_url or Redis is None or Queue is None:
        return None
    try:
        connection = Redis.from_url(settings.redis_url)
        connection.ping()
    except Exception:
        return None
    return Queue(QUEUE_NAME, connection=connection)


def _set_failed(db: Session, listing: Listing, message: str) -> None:
    listing.status = ListingStatus.FAILED
    listing.error_message = message[:1000]
    db.add(listing)
    db.commit()


async def _attempt_upload_once(listing_id: UUID, user_id: UUID, shop_id: UUID) -> None:
    db = SessionLocal()
    try:
        listing = db.get(Listing, listing_id)
        shop = db.get(Shop, shop_id)
        if not listing or not shop or listing.shop_id != shop.id or str(shop.user_id) != str(user_id):
            return
        etsy_listing_id = await full_upload_flow_with_refresh(db, shop, listing)
        listing.etsy_listing_id = etsy_listing_id
        listing.status = ListingStatus.LIVE
        listing.error_message = None
        db.add(listing)
        db.commit()
    finally:
        db.close()


async def _mark_upload_failed(listing_id: UUID, user_id: UUID, message: str, should_refund: bool) -> None:
    db = SessionLocal()
    try:
        listing = db.get(Listing, listing_id)
        if listing and should_refund:
            credit_service.refund_credits(
                db,
                user_id,
                "ETSY_LISTING_UPLOAD",
                listing_id=listing_id,
                reason="etsy_provider_error"
            )
        if listing:
            _set_failed(db, listing, message)
    finally:
        db.close()


async def _process_upload_job_with_retries(listing_id: UUID, user_id: UUID, shop_id: UUID) -> None:
    last_error = "Upload failed"
    should_refund = True
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            await _attempt_upload_once(listing_id, user_id, shop_id)
            return
        except Exception as exc:
            last_error = str(exc) if str(exc) else "Upload failed"
            should_refund = not isinstance(exc, (EtsyUploadAuthError, ValueError))
            if attempt < MAX_RETRIES:
                await asyncio.sleep(30 * (2 ** (attempt - 1)))
    await _mark_upload_failed(listing_id, user_id, last_error, should_refund)


def process_upload_job(listing_id: str, user_id: str, shop_id: str) -> None:
    asyncio.run(_process_upload_job_with_retries(UUID(listing_id), UUID(user_id), UUID(shop_id)))


async def _run_memory_job(job: InMemoryUploadJob) -> None:
    await _process_upload_job_with_retries(job.listing_id, job.user_id, job.shop_id)


async def _memory_worker() -> None:
    while True:
        now = datetime.now(timezone.utc)
        job: InMemoryUploadJob | None = None
        async with _memory_lock:
            ready_jobs = [candidate for candidate in _memory_jobs if candidate.run_at <= now]
            if ready_jobs:
                ready_jobs.sort(key=lambda candidate: candidate.run_at)
                job = ready_jobs[0]
                _memory_jobs.remove(job)

        if job:
            await _run_memory_job(job)
            continue
        await asyncio.sleep(1)


def _ensure_memory_worker() -> None:
    global _memory_worker_task
    if _memory_worker_task and not _memory_worker_task.done():
        return
    _memory_worker_task = asyncio.create_task(_memory_worker())


async def enqueue_upload_job(listing_id: UUID, user_id: UUID, shop_id: UUID, delay_seconds: int = 0) -> str:
    queue = _redis_queue()
    if queue is not None:
        job = queue.enqueue_in(
            timedelta(seconds=delay_seconds),
            process_upload_job,
            str(listing_id),
            str(user_id),
            str(shop_id),
            job_timeout=900
        )
        return str(job.id)

    job = InMemoryUploadJob(
        job_id=uuid.uuid4().hex,
        listing_id=listing_id,
        user_id=user_id,
        shop_id=shop_id,
        run_at=datetime.now(timezone.utc) + timedelta(seconds=delay_seconds)
    )
    async with _memory_lock:
        _memory_jobs.append(job)
    _ensure_memory_worker()
    return job.job_id


def job_payload(listing_id: UUID, user_id: UUID, shop_id: UUID) -> dict[str, Any]:
    return {
        "listing_id": str(listing_id),
        "user_id": str(user_id),
        "shop_id": str(shop_id)
    }
