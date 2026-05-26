from typing import Any
from datetime import datetime, timedelta, timezone
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from backend.app.models.credit_ledger import CreditAction, CreditLedger
from backend.app.models.user import User

CREDIT_COSTS = {
    "IMAGE_GENERATION": 5,
    "IMAGE_REGENERATION": 5,
    "HIGH_RES_IMAGE": 8,
    "VIDEO_GENERATION": 10,
    "COPY_GENERATION": 2,
    "ETSY_LISTING_UPLOAD": 3,
}

PLAN_MONTHLY_CREDITS = {
    "FREE": 0,
    "BASIC": 150,
    "PRO": 600,
    "AGENCY": 2000,
}

SIGNUP_CREDITS = 20


def get_balance(db: Session, user_id: UUID) -> int:
    balance = db.scalar(select(User.credit_balance).where(User.id == user_id))
    if balance is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    return int(balance)


def insufficient_credits_error(action: str, required: int, balance: int) -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_402_PAYMENT_REQUIRED,
        detail={
            "code": "INSUFFICIENT_CREDITS",
            "message": f"Insufficient credits for {action.replace('_', ' ').lower()}.",
            "required": required,
            "balance": balance,
            "action": action
        }
    )


def _deduct_credits_no_commit(
    db: Session,
    user_id: UUID,
    action: str,
    listing_id: UUID | None = None,
    job_id: UUID | None = None,
    idempotency_key: str | None = None
) -> int:
    cost = CREDIT_COSTS[action]
    new_balance = db.scalar(
        update(User)
        .where(User.id == user_id, User.credit_balance >= cost)
        .values(credit_balance=User.credit_balance - cost)
        .returning(User.credit_balance)
    )
    if new_balance is None:
        raise insufficient_credits_error(action, cost, get_balance(db, user_id))

    db.add(CreditLedger(
        user_id=user_id,
        action=CreditAction[action],
        credits_delta=-cost,
        balance_after=int(new_balance),
        listing_id=listing_id,
        job_id=job_id,
        idempotency_key=idempotency_key,
        metadata_json={}
    ))
    return int(new_balance)


def deduct_credits(
    db: Session,
    user_id: UUID,
    action: str,
    listing_id: UUID | None = None,
    job_id: UUID | None = None,
    idempotency_key: str | None = None
) -> int:
    new_balance = _deduct_credits_no_commit(db, user_id, action, listing_id, job_id, idempotency_key)
    db.commit()
    return new_balance


def grant_credits(
    db: Session,
    user_id: UUID,
    amount: int,
    action: CreditAction,
    idempotency_key: str,
    metadata: dict[str, Any] | None = None
) -> int:
    existing = db.scalar(select(CreditLedger.id).where(CreditLedger.idempotency_key == idempotency_key))
    if existing:
        return get_balance(db, user_id)

    new_balance = db.scalar(
        update(User)
        .where(User.id == user_id)
        .values(credit_balance=User.credit_balance + amount)
        .returning(User.credit_balance)
    )
    if new_balance is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    db.add(CreditLedger(
        user_id=user_id,
        action=action,
        credits_delta=amount,
        balance_after=int(new_balance),
        idempotency_key=idempotency_key,
        metadata_json=metadata or {}
    ))
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        return get_balance(db, user_id)
    return int(new_balance)


def refund_credits(
    db: Session,
    user_id: UUID,
    action: str,
    listing_id: UUID | None = None,
    reason: str = "provider_error"
) -> int:
    cost = CREDIT_COSTS[action]
    new_balance = db.scalar(
        update(User)
        .where(User.id == user_id)
        .values(credit_balance=User.credit_balance + cost)
        .returning(User.credit_balance)
    )
    if new_balance is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    db.add(CreditLedger(
        user_id=user_id,
        action=CreditAction.REFUND,
        credits_delta=cost,
        balance_after=int(new_balance),
        listing_id=listing_id,
        metadata_json={"original_action": action, "reason": reason}
    ))
    db.commit()
    return int(new_balance)


def grant_signup_credits(db: Session, user_id: UUID) -> int:
    return grant_credits(
        db,
        user_id,
        SIGNUP_CREDITS,
        CreditAction.SIGNUP_GRANT,
        idempotency_key=f"signup_{user_id}"
    )


def grant_plan_credits(db: Session, user_id: UUID, plan: str, period_start: int) -> int:
    amount = PLAN_MONTHLY_CREDITS.get(plan.upper(), 0)
    if amount == 0:
        return get_balance(db, user_id)
    return grant_credits(
        db,
        user_id,
        amount,
        CreditAction.MONTHLY_PLAN_GRANT,
        idempotency_key=f"plan_grant_{user_id}_{plan.upper()}_{period_start}",
        metadata={"plan": plan.upper(), "period_start": period_start}
    )


def _as_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def _user_plan_value(user: User) -> str:
    return getattr(user.plan, "value", str(user.plan)).upper()


def start_credit_cycle(db: Session, user_id: UUID, cycle_start: datetime) -> None:
    user = db.get(User, user_id)
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    cycle_start = _as_utc(cycle_start)
    user.credit_cycle_start = cycle_start
    user.credit_cycle_end = cycle_start + timedelta(days=30)
    db.add(user)
    db.commit()


def check_and_reset_credits_if_due(db: Session, user_id: UUID) -> dict:
    user = db.get(User, user_id)
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    now = datetime.now(timezone.utc)
    if user.credit_cycle_end is None:
        return {"reset": False, "reason": "no_cycle"}

    credit_cycle_end = _as_utc(user.credit_cycle_end)
    if now < credit_cycle_end:
        return {
            "reset": False,
            "reason": "cycle_not_ended",
            "ends_at": credit_cycle_end.isoformat()
        }

    if user.last_credit_reset is not None:
        last_credit_reset = _as_utc(user.last_credit_reset)
        if last_credit_reset >= credit_cycle_end - timedelta(minutes=5):
            return {"reset": False, "reason": "already_reset"}

    amount = PLAN_MONTHLY_CREDITS.get(_user_plan_value(user), 0)
    if amount > 0:
        idempotency_key = f"reset_{user_id}_{credit_cycle_end.isoformat()}"
        existing = db.scalar(select(CreditLedger.id).where(CreditLedger.idempotency_key == idempotency_key))
        if existing:
            user.last_credit_reset = now
        else:
            user.credit_balance = amount
            db.add(CreditLedger(
                user_id=user_id,
                action=CreditAction.MONTHLY_PLAN_GRANT,
                credits_delta=amount,
                balance_after=amount,
                idempotency_key=idempotency_key,
                metadata_json={"plan": _user_plan_value(user), "cycle_end": credit_cycle_end.isoformat()}
            ))

    user.last_credit_reset = now
    user.credit_cycle_start = credit_cycle_end
    user.credit_cycle_end = credit_cycle_end + timedelta(days=30)
    db.add(user)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        return {"reset": False, "reason": "already_reset"}

    return {
        "reset": True,
        "new_balance": user.credit_balance,
        "next_reset": _as_utc(user.credit_cycle_end).isoformat() if user.credit_cycle_end else None
    }


def reset_plan_credits(db: Session, user_id: UUID, plan: str, period_start: int) -> int:
    user = db.get(User, user_id)
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    normalized_plan = plan.upper()
    amount = PLAN_MONTHLY_CREDITS.get(normalized_plan, 0)
    if amount == 0:
        user.credit_balance = 0
        db.add(user)
        db.commit()
        return 0

    idempotency_key = f"plan_reset_{user_id}_{normalized_plan}_{period_start}"
    existing = db.scalar(select(CreditLedger.id).where(CreditLedger.idempotency_key == idempotency_key))
    if existing:
        return get_balance(db, user_id)

    user.credit_balance = amount
    user.last_credit_reset = datetime.now(timezone.utc)
    db.add(CreditLedger(
        user_id=user_id,
        action=CreditAction.MONTHLY_PLAN_GRANT,
        credits_delta=amount,
        balance_after=amount,
        idempotency_key=idempotency_key,
        metadata_json={"plan": normalized_plan, "period_start": period_start, "reset": True}
    ))
    db.add(user)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        return get_balance(db, user_id)
    return amount


def get_credit_status(db: Session, user_id: UUID) -> dict:
    user = db.get(User, user_id)
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    check_and_reset_credits_if_due(db, user_id)
    user = db.get(User, user_id)
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    db.refresh(user)

    now = datetime.now(timezone.utc)
    days_until_reset = None
    if user.credit_cycle_end:
        credit_cycle_end = _as_utc(user.credit_cycle_end)
        days_until_reset = max(0, (credit_cycle_end - now).days)

    plan_credits = PLAN_MONTHLY_CREDITS.get(_user_plan_value(user), 0)
    software_percent = int((user.credit_balance / plan_credits) * 100) if plan_credits > 0 else 0
    return {
        "software_credits": {
            "balance": user.credit_balance,
            "plan_total": plan_credits,
            "percent_remaining": software_percent,
            "depleted": user.credit_balance == 0,
            "low": software_percent <= 20 and software_percent > 0,
            "days_until_reset": days_until_reset,
            "reset_at": _as_utc(user.credit_cycle_end).isoformat() if user.credit_cycle_end else None
        },
        "plan": _user_plan_value(user),
        "cycle_start": _as_utc(user.credit_cycle_start).isoformat() if user.credit_cycle_start else None,
        "cycle_end": _as_utc(user.credit_cycle_end).isoformat() if user.credit_cycle_end else None
    }
