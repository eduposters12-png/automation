from typing import Any
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
