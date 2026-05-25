from pydantic import BaseModel

from backend.app.models.user import Plan


class DashboardStats(BaseModel):
    shop_name: str | None
    shop_url: str | None
    plan: Plan
    total_listings: int
    monthly_usage: int
    monthly_limit: int | None
    shop_limit: int
    etsy_connected: bool
    claude_key_added: bool
