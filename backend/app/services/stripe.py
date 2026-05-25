from backend.app.core.config import get_settings
from backend.app.models.user import Plan


def price_id_for_plan(plan: Plan) -> str:
    settings = get_settings()
    return {
        Plan.BASIC: settings.stripe_basic_price_id,
        Plan.PRO: settings.stripe_pro_price_id,
        Plan.AGENCY: settings.stripe_agency_price_id
    }[plan]


def plan_for_price_id(price_id: str) -> Plan:
    settings = get_settings()
    if price_id == settings.stripe_basic_price_id:
        return Plan.BASIC
    if price_id == settings.stripe_pro_price_id:
        return Plan.PRO
    if price_id == settings.stripe_agency_price_id:
        return Plan.AGENCY
    return Plan.FREE
