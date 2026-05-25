import uuid

from pydantic import BaseModel
from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.orm import Session
import stripe as stripe_sdk

from backend.app.core.config import get_settings
from backend.app.core.deps import get_current_user
from backend.app.core.plans import normalize_plan
from backend.app.db.session import get_db
from backend.app.models.user import Plan, User
from backend.app.services.stripe import plan_for_price_id, price_id_for_plan

router = APIRouter(prefix="/stripe", tags=["stripe"])


class CheckoutRequest(BaseModel):
    plan: str


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
            line_items=[{"price": price_id_for_plan(plan), "quantity": 1}],
            success_url=f"{frontend_url}/dashboard?checkout=success",
            cancel_url=f"{frontend_url}/upgrade?checkout=cancelled",
            allow_promotion_codes=True,
            metadata={"user_id": str(current_user.id), "plan": plan.value},
            subscription_data={"metadata": {"user_id": str(current_user.id), "plan": plan.value}}
        )
    except stripe_sdk.error.StripeError as exc:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(exc)) from exc

    return CheckoutResponse(url=session["url"])


def _subscription_plan(subscription: dict) -> Plan:
    items = subscription.get("items", {}).get("data", [])
    if not items:
        return Plan.FREE
    price_id = items[0].get("price", {}).get("id")
    return plan_for_price_id(price_id)


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
            user.stripe_customer_id = obj.get("customer") or user.stripe_customer_id
            user.stripe_subscription_id = obj.get("subscription") or user.stripe_subscription_id
            db.add(user)
            db.commit()

    if event_type in {"customer.subscription.created", "customer.subscription.updated"}:
        customer_id = obj.get("customer")
        user = db.scalar(select(User).where(User.stripe_customer_id == customer_id))
        if user:
            status_value = obj.get("status")
            user.plan = _subscription_plan(obj) if status_value in {"active", "trialing"} else Plan.FREE
            user.stripe_subscription_id = obj.get("id") or user.stripe_subscription_id
            db.add(user)
            db.commit()

    if event_type == "customer.subscription.deleted":
        customer_id = obj.get("customer")
        user = db.scalar(select(User).where(User.stripe_customer_id == customer_id))
        if user:
            user.plan = Plan.FREE
            user.stripe_subscription_id = None
            db.add(user)
            db.commit()

    return {"received": True}
