from backend.app.models.user import Plan

PLAN_LIMITS = {
    Plan.FREE: {"listings": 0, "shops": 1, "label": "Free"},
    Plan.BASIC: {"listings": 20, "shops": 1, "label": "Basic"},
    Plan.PRO: {"listings": 100, "shops": 3, "label": "Pro"},
    Plan.AGENCY: {"listings": None, "shops": 10, "label": "Agency"}
}


def normalize_plan(plan_id: str) -> Plan:
    normalized = plan_id.upper()
    if normalized not in Plan.__members__:
        raise ValueError("Unknown plan")
    return Plan[normalized]
