from backend.app.core.config import get_settings
from backend.app.models.user import Plan


def price_id_for_plan(plan: Plan, annual: bool = False) -> str:
    settings = get_settings()
    if annual:
        annual_prices = {
            Plan.BASIC: settings.stripe_annual_basic_price_id,
            Plan.PRO: settings.stripe_annual_pro_price_id,
            Plan.AGENCY: settings.stripe_annual_agency_price_id
        }
        if annual_prices[plan]:
            return annual_prices[plan]
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
    if price_id == settings.stripe_annual_basic_price_id:
        return Plan.BASIC
    if price_id == settings.stripe_annual_pro_price_id:
        return Plan.PRO
    if price_id == settings.stripe_annual_agency_price_id:
        return Plan.AGENCY
    return Plan.FREE
