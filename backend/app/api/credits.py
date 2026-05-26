from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.app.core.deps import get_current_user
from backend.app.db.session import get_db
from backend.app.models.credit_ledger import CreditLedger
from backend.app.models.user import User
from backend.app.services.credit_service import get_balance

router = APIRouter(prefix="/credits", tags=["credits"])


@router.get("/balance")
def credit_balance(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> dict[str, int | str]:
    return {"credit_balance": get_balance(db, current_user.id), "plan": current_user.plan.value}


@router.get("/history")
def credit_history(
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> list[dict[str, str | int | None]]:
    entries = db.scalars(
        select(CreditLedger)
        .where(CreditLedger.user_id == current_user.id)
        .order_by(CreditLedger.created_at.desc())
        .offset(offset)
        .limit(limit)
    ).all()
    return [
        {
            "action": entry.action.value,
            "credits_delta": entry.credits_delta,
            "balance_after": entry.balance_after,
            "created_at": entry.created_at.isoformat(),
            "listing_id": str(entry.listing_id) if entry.listing_id else None
        }
        for entry in entries
    ]
