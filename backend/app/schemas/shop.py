from datetime import datetime
from typing import Any

from pydantic import BaseModel


class ShopAnalysisResponse(BaseModel):
    analyzed: bool
    analysis: dict[str, Any] | None = None
    last_analyzed_at: datetime | None = None
