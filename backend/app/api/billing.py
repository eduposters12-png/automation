import uuid
from datetime import datetime, timezone

from pydantic import BaseModel
from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.orm import Session
import stripe as stripe_sdk

from backend.app.core.config import get_settings
from backend.app.core.deps import get_current_user
from backend.app.core.plans import normalize_plan
from backend.app.core.security import decrypt_secret
from backend.app.db.session import get_db
from backend.app.models.user import Plan, User
from backend.app.services import credit_service
from backend.app.services.claude_balance_service import check_claude_key_status
from backend.app.services.shops import get_primary_shop
from backend.app.services.stripe import plan_for_price_id, price_id_for_plan

router = APIRouter(prefix="/stripe", tags=["stripe"])


class CheckoutRequest(BaseModel):
    plan: str
    annual: bool = False


class CheckoutResponse(BaseModel):
    url: str


@router.post("/checkout", response_model=CheckoutResponse)
def create_checkout_session(
    payload: CheckoutRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> CheckoutResponse:
    try:
        plan = normalize_plan(payload.plan)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid plan") from exc

    if plan == Plan.FREE:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Free plan does not use checkout")

    settings = get_settings()
    stripe_sdk.api_key = settings.stripe_secret_key
    frontend_url = str(settings.frontend_url).rstrip("/")

    try:
        if not current_user.stripe_customer_id:
            customer = stripe_sdk.Customer.create(
                email=current_user.email,
                name=current_user.name,
                metadata={"user_id": str(current_user.id)}
            )
            current_user.stripe_customer_id = customer["id"]
            db.add(current_user)
            db.commit()
            db.refresh(current_user)

        session = stripe_sdk.checkout.Session.create(
            customer=current_user.stripe_customer_id,
            mode="subscription",
            payment_method_types=["card"],
            line_items=[{"price": price_id_for_plan(plan, annual=payload.annual), "quantity": 1}],
            success_url=f"{frontend_url}/dashboard?checkout=success",
            cancel_url=f"{frontend_url}/upgrade?checkout=cancelled",
            allow_promotion_codes=True,
            metadata={"user_id": str(current_user.id), "plan": plan.value},
            subscription_data={"metadata": {"user_id": str(current_user.id), "plan": plan.value}}
        )
    except stripe_sdk.error.StripeError as exc:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(exc)) from exc

    return CheckoutResponse(url=session["url"])


@router.post("/cancel")
def cancel_subscription(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> dict[str, bool]:
    settings = get_settings()
    stripe_sdk.api_key = settings.stripe_secret_key
    if current_user.stripe_subscription_id:
        try:
            stripe_sdk.Subscription.delete(current_user.stripe_subscription_id)
        except stripe_sdk.error.StripeError as exc:
            raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(exc)) from exc
    current_user.plan = Plan.FREE
    current_user.stripe_subscription_id = None
    db.add(current_user)
    db.commit()
    return {"success": True}


def _subscription_plan(subscription: dict) -> Plan:
    items = subscription.get("items", {}).get("data", [])
    if not items:
        return Plan.FREE
    price_id = items[0].get("price", {}).get("id")
    return plan_for_price_id(price_id)


def _subscription_period_start(subscription: dict) -> int:
    return int(
        subscription.get("current_period_start")
        or subscription.get("created")
        or datetime.now(timezone.utc).timestamp()
    )


def _safe_retrieve_subscription(subscription_id: str | None) -> dict | None:
    if not subscription_id:
        return None
    try:
        return stripe_sdk.Subscription.retrieve(subscription_id)
    except stripe_sdk.error.StripeError:
        return None


def _checkout_plan(session: dict, subscription: dict | None = None) -> Plan:
    metadata_plan = session.get("metadata", {}).get("plan")
    if metadata_plan:
        try:
            return normalize_plan(metadata_plan)
        except ValueError:
            pass
    if subscription:
        return _subscription_plan(subscription)
    return Plan.FREE


def _checkout_period_start(session: dict, subscription: dict | None = None) -> int:
    metadata_period_start = session.get("metadata", {}).get("period_start")
    if metadata_period_start:
        try:
            return int(metadata_period_start)
        except (TypeError, ValueError):
            pass
    if subscription:
        return _subscription_period_start(subscription)
    return int(datetime.now(timezone.utc).timestamp())


def _invoice_plan(invoice: dict) -> Plan:
    lines = invoice.get("lines", {}).get("data", [])
    if not lines:
        return Plan.FREE
    price_id = lines[0].get("price", {}).get("id")
    return plan_for_price_id(price_id)


def _invoice_period_start(invoice: dict) -> int:
    lines = invoice.get("lines", {}).get("data", [])
    if lines:
        period_start = lines[0].get("period", {}).get("start")
        if period_start:
            return int(period_start)
    return int(invoice.get("period_start") or invoice.get("created") or datetime.now(timezone.utc).timestamp())


@router.post("/webhook")
async def stripe_webhook(request: Request, db: Session = Depends(get_db)) -> dict[str, bool]:
    settings = get_settings()
    stripe_sdk.api_key = settings.stripe_secret_key
    payload = await request.body()
    signature = request.headers.get("stripe-signature")

    try:
        event = stripe_sdk.Webhook.construct_event(
            payload=payload,
            sig_header=signature,
            secret=settings.stripe_webhook_secret
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid payload") from exc
    except stripe_sdk.error.SignatureVerificationError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid signature") from exc

    event_type = event["type"]
    obj = event["data"]["object"]

    if event_type == "checkout.session.completed":
        user_id = obj.get("metadata", {}).get("user_id")
        try:
            user = db.get(User, uuid.UUID(user_id)) if user_id else None
        except ValueError:
            user = None
        if user:
            subscription = _safe_retrieve_subscription(obj.get("subscription"))
            new_plan = _checkout_plan(obj, subscription)
            period_start = _checkout_period_start(obj, subscription)
            user.stripe_customer_id = obj.get("customer") or user.stripe_customer_id
            user.stripe_subscription_id = obj.get("subscription") or user.stripe_subscription_id
            if new_plan != Plan.FREE:
                user.plan = new_plan
            db.add(user)
            db.commit()
            if new_plan != Plan.FREE:
                credit_service.start_credit_cycle(
                    db,
                    user.id,
                    datetime.fromtimestamp(period_start, tz=timezone.utc)
                )
                credit_service.reset_plan_credits(db, user.id, new_plan.value, period_start)

    if event_type in {"customer.subscription.created", "customer.subscription.updated"}:
        customer_id = obj.get("customer")
        user = db.scalar(select(User).where(User.stripe_customer_id == customer_id))
        if user:
            status_value = obj.get("status")
            new_plan = _subscription_plan(obj) if status_value in {"active", "trialing"} else Plan.FREE
            user.plan = new_plan
            user.stripe_subscription_id = obj.get("id") or user.stripe_subscription_id
            db.add(user)
            db.commit()
            if new_plan != Plan.FREE:
                current_period_start = _subscription_period_start(obj)
                credit_service.start_credit_cycle(
                    db,
                    user.id,
                    datetime.fromtimestamp(current_period_start, tz=timezone.utc)
                )
                credit_service.reset_plan_credits(db, user.id, new_plan.value, current_period_start)

    if event_type == "invoice.payment_succeeded":
        customer_id = obj.get("customer")
        user = db.scalar(select(User).where(User.stripe_customer_id == customer_id))
        if user:
            plan = _invoice_plan(obj)
            if plan != Plan.FREE:
                period_start = _invoice_period_start(obj)
                user.plan = plan
                db.add(user)
                db.commit()
                credit_service.start_credit_cycle(
                    db,
                    user.id,
                    datetime.fromtimestamp(period_start, tz=timezone.utc)
                )
                credit_service.reset_plan_credits(db, user.id, plan.value, period_start)

    if event_type == "customer.subscription.deleted":
        customer_id = obj.get("customer")
        user = db.scalar(select(User).where(User.stripe_customer_id == customer_id))
        if user:
            user.plan = Plan.FREE
            user.stripe_subscription_id = None
            user.credit_cycle_start = None
            user.credit_cycle_end = None
            user.credit_balance = 0
            db.add(user)
            db.commit()

    return {"received": True}


@router.get("/credit-status")
async def credit_status(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> dict[str, object]:
    shop = get_primary_shop(db, current_user)
    software_status = credit_service.get_credit_status(db, current_user.id)

    if shop and shop.claude_api_key_encrypted:
        claude_key = decrypt_secret(shop.claude_api_key_encrypted)
        claude_status = await check_claude_key_status(claude_key, user_id=current_user.id)
    else:
        claude_status = {
            "working": False,
            "status": "no_key",
            "message": "No Claude API key configured"
        }

    software_depleted = software_status["software_credits"]["depleted"]
    claude_exhausted = claude_status["status"] in {"credits_exhausted", "invalid_key"}

    if software_depleted and claude_exhausted:
        alert_state = "both_depleted"
    elif software_depleted:
        alert_state = "software_depleted"
    elif claude_exhausted:
        alert_state = "claude_depleted"
    elif software_status["software_credits"]["low"]:
        alert_state = "software_low"
    else:
        alert_state = "ok"

    return {
        "alert_state": alert_state,
        "software_credits": software_status["software_credits"],
        "claude": {
            "working": claude_status["working"],
            "status": claude_status["status"],
            "message": claude_status["message"]
        },
        "plan": software_status["plan"],
        "cycle_end": software_status["cycle_end"],
        "days_until_reset": software_status["software_credits"]["days_until_reset"]
    }
