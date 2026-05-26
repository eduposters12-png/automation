from functools import lru_cache

from pydantic import AnyHttpUrl, Field, field_validator
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
        default="shops_r shops_w listings_r listings_w transactions_r",
        alias="ETSY_SCOPES"
    )
    serper_api_key: str = Field(default="", alias="SERPER_API_KEY")
    openai_api_key: str = Field(default="", alias="OPENAI_API_KEY")
    gemini_api_key: str = Field(default="", alias="GEMINI_API_KEY")
    redis_url: str = Field(default="", alias="REDIS_URL")
    cloudinary_cloud_name: str = Field(default="", alias="CLOUDINARY_CLOUD_NAME")
    cloudinary_api_key: str = Field(default="", alias="CLOUDINARY_API_KEY")
    cloudinary_api_secret: str = Field(default="", alias="CLOUDINARY_API_SECRET")

    stripe_secret_key: str = Field(alias="STRIPE_SECRET_KEY")
    stripe_webhook_secret: str = Field(alias="STRIPE_WEBHOOK_SECRET")
    stripe_basic_price_id: str = Field(alias="STRIPE_BASIC_PRICE_ID")
    stripe_pro_price_id: str = Field(alias="STRIPE_PRO_PRICE_ID")
    stripe_agency_price_id: str = Field(alias="STRIPE_AGENCY_PRICE_ID")
    stripe_annual_basic_price_id: str = Field(default="", alias="STRIPE_ANNUAL_BASIC_PRICE_ID")
    stripe_annual_pro_price_id: str = Field(default="", alias="STRIPE_ANNUAL_PRO_PRICE_ID")
    stripe_annual_agency_price_id: str = Field(default="", alias="STRIPE_ANNUAL_AGENCY_PRICE_ID")

    cookie_name: str = "listify_session"
    cookie_domain: str | None = Field(default=None, alias="COOKIE_DOMAIN")
    cookie_secure: bool = False
    access_token_expire_minutes: int = 60 * 24 * 7

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    @field_validator("cookie_domain", mode="before")
    @classmethod
    def empty_cookie_domain_to_none(cls, value: str | None) -> str | None:
        if value == "":
            return None
        return value


@lru_cache
def get_settings() -> Settings:
    return Settings()
