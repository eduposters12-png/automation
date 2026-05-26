from pydantic import BaseModel


class EtsyConnectionStatus(BaseModel):
    connected: bool
    shop_name: str | None = None
    shop_url: str | None = None
    etsy_shop_id: str | None = None
    connected_at: str | None = None


class EtsyDisconnectResponse(BaseModel):
    success: bool
    message: str
