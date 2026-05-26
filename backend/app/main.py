from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.app.api import analytics, auth, billing, dashboard, etsy, jobs, listings, onboarding, settings, shop
from backend.app.core.config import get_settings
from backend.app.middleware.rate_limit import configure_rate_limit
from backend.app.middleware.request_logging import configure_request_logging
from backend.app.middleware.security import configure_security_middleware

settings_obj = get_settings()

app = FastAPI(
    title="ListifyAI API",
    version="0.1.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[str(settings_obj.frontend_url).rstrip("/")],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"]
)
configure_security_middleware(app)
configure_request_logging(app)
configure_rate_limit(app)

app.include_router(auth.router)
app.include_router(etsy.router)
app.include_router(onboarding.router)
app.include_router(dashboard.router)
app.include_router(settings.router)
app.include_router(billing.router)
app.include_router(jobs.router)
app.include_router(listings.router)
app.include_router(shop.router)
app.include_router(analytics.router)
app.include_router(analytics.shop_router)


@app.get("/health")
def health() -> dict[str, str]:
    return analytics.health_payload()
