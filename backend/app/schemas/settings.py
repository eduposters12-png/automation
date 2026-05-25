from pydantic import BaseModel, Field


class SettingsResponse(BaseModel):
    name: str
    email: str
    plan: str
    shop_name: str | None
    shop_url: str | None
    niche: str | None
    etsy_connected: bool
    claude_key_added: bool


class SettingsUpdateRequest(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=160)
    shop_url: str | None = Field(default=None, max_length=500)
    niche: str | None = Field(default=None, max_length=255)
    claude_api_key: str | None = Field(default=None, min_length=10, max_length=500)
