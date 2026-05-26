from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.app.models.usage import Usage, UsageAction
from backend.app.models.user import Plan, User

PLAN_LIMITS: dict[Plan, dict[UsageAction, int]] = {
    Plan.FREE: {
        UsageAction.IMAGE_GENERATED: 0,
        UsageAction.VIDEO_GENERATED: 0,
        UsageAction.LISTING_UPLOADED: 0
    },
    Plan.BASIC: {
        UsageAction.IMAGE_GENERATED: 20,
        UsageAction.VIDEO_GENERATED: 0,
        UsageAction.LISTING_UPLOADED: 20
    },
    Plan.PRO: {
        UsageAction.IMAGE_GENERATED: 100,
        UsageAction.VIDEO_GENERATED: 50,
        UsageAction.LISTING_UPLOADED: 100
    },
    Plan.AGENCY: {
        UsageAction.IMAGE_GENERATED: 500,
        UsageAction.VIDEO_GENERATED: 200,
        UsageAction.LISTING_UPLOADED: 500
    }
}


def current_month() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m")


def _action(value: str | UsageAction) -> UsageAction:
    return value if isinstance(value, UsageAction) else UsageAction(value)


def track_usage(user_id: str | UUID, action: str | UsageAction, db: Session) -> None:
    usage_action = _action(action)
    month = current_month()
    row = db.scalar(
        select(Usage).where(
            Usage.user_id == UUID(str(user_id)),
            Usage.action == usage_action,
            Usage.month == month
        )
    )
    if not row:
        row = Usage(user_id=UUID(str(user_id)), action=usage_action, month=month, count=0)
    row.count += 1
    db.add(row)
    db.commit()


def get_usage_this_month(user_id: str | UUID, db: Session) -> dict[str, int]:
    month = current_month()
    rows = db.scalars(
        select(Usage).where(Usage.user_id == UUID(str(user_id)), Usage.month == month)
    ).all()
    usage = {action.value: 0 for action in UsageAction}
    for row in rows:
        usage[row.action.value] = row.count
    return usage


def check_plan_limit(user_id: str | UUID, action: str | UsageAction, db: Session) -> dict[str, int | bool]:
    usage_action = _action(action)
    user = db.get(User, UUID(str(user_id)))
    plan = user.plan if user else Plan.FREE
    limit = PLAN_LIMITS[plan][usage_action]
    used = get_usage_this_month(user_id, db)[usage_action.value]
    return {"allowed": used < limit, "used": used, "limit": limit}


def usage_with_limits(user: User, db: Session) -> dict[str, dict[str, int]]:
    usage = get_usage_this_month(user.id, db)
    return {
        action.value: {
            "used": usage[action.value],
            "limit": PLAN_LIMITS[user.plan][action]
        }
        for action in UsageAction
    }
