from typing import Any
from uuid import UUID

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy import func, select, update
from sqlalchemy.orm import Session

from backend.app.core.deps import get_current_user
from backend.app.db.session import get_db
from backend.app.models.automation_config import AutoLogEvent, AutoMode, AutomationConfig, AutomationLog, QualityMode
from backend.app.models.notification import Notification, NotificationType
from backend.app.models.user import Plan, User
from backend.app.services import credit_calculator, credit_service
from backend.app.services.automation_engine import (
    append_user_topics,
    normalise_topic,
    remove_topic,
    run_auto_cycle_background,
    send_notification
)
from backend.app.services.shops import get_or_create_primary_shop, get_primary_shop

router = APIRouter(prefix="/automation", tags=["automation"])
notifications_router = APIRouter(prefix="/notifications", tags=["notifications"])


class TopicIn(BaseModel):
    topic: str = Field(min_length=1, max_length=200)
    description: str = Field(default="", max_length=2000)


class AutomationConfigUpdate(BaseModel):
    mode: AutoMode | None = None
    topics: list[TopicIn] | None = None
    remove_topic_id: str | None = None
    daily_limit: int | None = Field(default=None, ge=1, le=50)
    target_min_listings: int | None = Field(default=None, ge=1)
    target_max_listings: int | None = Field(default=None, ge=1)
    quality_mode: QualityMode | None = None
    auto_quality_adjust: bool | None = None


def _enum_value(value: Any) -> str:
    return getattr(value, "value", str(value))


def _config_out(config: AutomationConfig) -> dict[str, Any]:
    return {
        "mode": _enum_value(config.mode),
        "topics_json": [normalise_topic(topic, str(topic.get("status") or "pending")) for topic in (config.topics_json or []) if isinstance(topic, dict)],
        "daily_limit": config.daily_limit,
        "target_min_listings": config.target_min_listings,
        "target_max_listings": config.target_max_listings,
        "quality_mode": _enum_value(config.quality_mode),
        "auto_quality_adjust": config.auto_quality_adjust,
        "is_running": config.is_running,
        "listings_created_today": config.listings_created_today,
        "listings_created_total": config.listings_created_total,
        "last_run_at": config.last_run_at.isoformat() if config.last_run_at else None
    }


def _notification_out(notification: Notification) -> dict[str, Any]:
    return {
        "id": str(notification.id),
        "type": _enum_value(notification.type),
        "title": notification.title,
        "message": notification.message,
        "is_read": notification.is_read,
        "action_url": notification.action_url,
        "metadata_json": notification.metadata_json or {},
        "created_at": notification.created_at.isoformat()
    }


def _log_out(log: AutomationLog) -> dict[str, Any]:
    return {
        "id": str(log.id),
        "event_type": _enum_value(log.event_type),
        "message": log.message,
        "metadata_json": log.metadata_json or {},
        "created_at": log.created_at.isoformat()
    }


def _get_or_create_config(db: Session, current_user: User) -> AutomationConfig:
    shop = get_or_create_primary_shop(db, current_user)
    config = db.scalar(select(AutomationConfig).where(AutomationConfig.shop_id == shop.id))
    if config:
        return config
    config = AutomationConfig(
        shop_id=shop.id,
        mode=AutoMode.MANUAL,
        topics_json=[],
        daily_limit=10,
        quality_mode=QualityMode.FULL,
        auto_quality_adjust=True,
        is_running=False,
        listings_created_today=0,
        listings_created_total=0
    )
    db.add(config)
    db.commit()
    db.refresh(config)
    return config


def _notify_manual_pause_if_needed(db: Session, current_user: User, config: AutomationConfig) -> None:
    for topic in config.topics_json or []:
        if isinstance(topic, dict) and topic.get("status") == "in_progress":
            topic_id = str(topic.get("id") or "")
            topic_name = str(topic.get("topic") or "this topic")
            send_notification(
                db,
                current_user.id,
                NotificationType.AUTO_PAUSED,
                "Auto mode paused — action required",
                f"Topic {topic_name} is currently in progress. Delete it or keep it paused where it left off.",
                {
                    "topic_id": topic_id,
                    "topic": topic_name,
                    "actions": ["delete_topic", "keep_paused"]
                },
                "/automation"
            )


@router.get("/config")
def get_config(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> dict[str, Any]:
    return _config_out(_get_or_create_config(db, current_user))


@router.post("/config")
def update_config(
    payload: AutomationConfigUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> dict[str, Any]:
    config = _get_or_create_config(db, current_user)
    previous_mode = config.mode

    if payload.target_max_listings is not None:
        target_min = payload.target_min_listings if payload.target_min_listings is not None else config.target_min_listings
        if target_min is not None and payload.target_max_listings < target_min:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="target_max_listings must be greater than or equal to target_min_listings")

    if payload.remove_topic_id:
        remove_topic(config, payload.remove_topic_id)
    if payload.mode is not None:
        config.mode = payload.mode
        if payload.mode == AutoMode.MANUAL:
            config.is_running = False
    if payload.topics is not None:
        append_user_topics(config, [topic.model_dump() for topic in payload.topics])
    if payload.daily_limit is not None:
        config.daily_limit = payload.daily_limit
    if payload.target_min_listings is not None:
        config.target_min_listings = payload.target_min_listings
    if payload.target_max_listings is not None:
        config.target_max_listings = payload.target_max_listings
    if payload.quality_mode is not None:
        config.quality_mode = payload.quality_mode
    if payload.auto_quality_adjust is not None:
        config.auto_quality_adjust = payload.auto_quality_adjust

    if previous_mode in {AutoMode.AUTO, AutoMode.HYBRID} and config.mode == AutoMode.MANUAL:
        _notify_manual_pause_if_needed(db, current_user, config)

    db.add(config)
    db.commit()
    db.refresh(config)
    return _config_out(config)


@router.post("/start")
def start_automation(
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> dict[str, Any]:
    config = _get_or_create_config(db, current_user)
    shop = get_primary_shop(db, current_user)
    if not shop:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Connect your Etsy shop first")
    if config.mode == AutoMode.MANUAL:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Cannot start auto in manual mode")
    if current_user.plan not in {Plan.PRO, Plan.AGENCY}:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Upgrade to Pro to start automation.")
    balance = int(credit_service.get_credit_status(db, current_user.id)["software_credits"]["balance"])
    if balance < credit_calculator.cost_per_listing("FAST"):
        raise credit_service.insufficient_credits_error("AUTOMATION", credit_calculator.cost_per_listing("FAST"), balance)

    config.is_running = True
    db.add(config)
    db.commit()
    background_tasks.add_task(run_auto_cycle_background, str(shop.id))
    return {"started": True, "mode": _enum_value(config.mode)}


@router.post("/stop")
def stop_automation(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> dict[str, bool]:
    config = _get_or_create_config(db, current_user)
    config.is_running = False
    db.add(config)
    db.commit()
    return {"stopped": True}


@router.get("/preview")
def preview_automation(
    quality_mode: QualityMode | None = Query(default=None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> dict[str, Any]:
    config = _get_or_create_config(db, current_user)
    balance = int(credit_service.get_credit_status(db, current_user.id)["software_credits"]["balance"])
    preview = {
        quality: credit_calculator.calculate_listings_possible(balance, quality)
        for quality in ("FULL", "BALANCED", "FAST")
    }
    recommendation = None
    if config.target_min_listings and config.target_max_listings:
        recommendation = credit_calculator.suggest_quality_for_target(
            balance,
            config.target_min_listings,
            config.target_max_listings
        )
    return {
        "credit_balance": balance,
        "preview": preview,
        "recommendation": recommendation,
        "current_quality": _enum_value(quality_mode or config.quality_mode),
        "target_min": config.target_min_listings,
        "target_max": config.target_max_listings
    }


@router.get("/logs")
def automation_logs(
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> list[dict[str, Any]]:
    shop = get_primary_shop(db, current_user)
    if not shop:
        return []
    logs = db.scalars(
        select(AutomationLog)
        .where(AutomationLog.shop_id == shop.id)
        .order_by(AutomationLog.created_at.desc())
        .offset(offset)
        .limit(limit)
    ).all()
    return [_log_out(log) for log in logs]


@notifications_router.get("")
def list_notifications(
    limit: int = Query(default=20, ge=1, le=100),
    unread_only: bool = Query(default=False),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> list[dict[str, Any]]:
    conditions = [Notification.user_id == current_user.id]
    if unread_only:
        conditions.append(Notification.is_read.is_(False))
    notifications = db.scalars(
        select(Notification)
        .where(*conditions)
        .order_by(Notification.created_at.desc())
        .limit(limit)
    ).all()
    return [_notification_out(notification) for notification in notifications]


@notifications_router.post("/{notification_id}/read")
def mark_notification_read(
    notification_id: UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> dict[str, bool]:
    notification = db.get(Notification, notification_id)
    if not notification or notification.user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Notification not found")
    notification.is_read = True
    db.add(notification)
    db.commit()
    return {"success": True}


@notifications_router.post("/read-all")
def mark_all_notifications_read(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> dict[str, int | bool]:
    result = db.execute(
        update(Notification)
        .where(Notification.user_id == current_user.id, Notification.is_read.is_(False))
        .values(is_read=True)
    )
    db.commit()
    return {"success": True, "count": int(result.rowcount or 0)}


@notifications_router.get("/unread-count")
def unread_count(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> dict[str, int]:
    count = db.scalar(
        select(func.count())
        .select_from(Notification)
        .where(Notification.user_id == current_user.id, Notification.is_read.is_(False))
    ) or 0
    return {"count": int(count)}
