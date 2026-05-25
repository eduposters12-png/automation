from functools import lru_cache

from pydantic import AnyHttpUrl, Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    database_url: str = Field(alias="DATABASE_URL")
    jwt_secret: str = Field(alias="JWT_SECRET")
    frontend_url: AnyHttpUrl = Field(alias="FRONTEND_URL")
    backend_url: AnyHttpUrl = Field(alias="BACKEND_URL")
    encryption_key: str = Field(alias="ENCRYPTION_KEY")

    etsy_client_id: str = Field(alias="ETSY_CLIENT_ID")
    etsy_redirect_uri: AnyHttpUrl = Field(alias="ETSY_REDIRECT_URI")
    etsy_scopes: str = Field(
        default="shops_r shops_w listings_r listings_w",
        alias="ETSY_SCOPES"
    )

    stripe_secret_key: str = Field(alias="STRIPE_SECRET_KEY")
    stripe_webhook_secret: str = Field(alias="STRIPE_WEBHOOK_SECRET")
    stripe_basic_price_id: str = Field(alias="STRIPE_BASIC_PRICE_ID")
    stripe_pro_price_id: str = Field(alias="STRIPE_PRO_PRICE_ID")
    stripe_agency_price_id: str = Field(alias="STRIPE_AGENCY_PRICE_ID")

    cookie_name: str = "listify_session"
    cookie_secure: bool = False
    access_token_expire_minutes: int = 60 * 24 * 7

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


@lru_cache
def get_settings() -> Settings:
    return Settings()
