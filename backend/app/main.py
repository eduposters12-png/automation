from pathlib import Path
import sys

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

project_root = Path(__file__).resolve().parents[2]
project_root_string = str(project_root)

if project_root_string not in sys.path:
    sys.path.insert(0, project_root_string)

from backend.app.api import analytics, auth, billing, credits, dashboard, etsy, jobs, listings, onboarding, settings, shop
from backend.app.core.config import get_settings
from backend.app.middleware.rate_limit import configure_rate_limit
from backend.app.middleware.request_logging import configure_request_logging
from backend.app.middleware.security import configure_security_middleware

settings_obj = get_settings()
frontend_origin = str(settings_obj.frontend_url).rstrip("/")
allowed_origins = {
    frontend_origin,
    frontend_origin.replace("localhost", "127.0.0.1"),
    frontend_origin.replace("127.0.0.1", "localhost")
}

app = FastAPI(
    title="ListifyAI API",
    version="0.1.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=sorted(allowed_origins),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"]
)
configure_security_middleware(app)
configure_request_logging(app)
configure_rate_limit(app)


@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException) -> JSONResponse:
    return JSONResponse(status_code=exc.status_code, content={"detail": exc.detail}, headers=exc.headers)


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
app.include_router(credits.router)


@app.get("/health")
def health() -> dict[str, str]:
    return analytics.health_payload()
