from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.app.api import auth, billing, dashboard, etsy, jobs, listings, onboarding, settings
from backend.app.core.config import get_settings

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

app.include_router(auth.router)
app.include_router(etsy.router)
app.include_router(onboarding.router)
app.include_router(dashboard.router)
app.include_router(settings.router)
app.include_router(billing.router)
app.include_router(jobs.router)
app.include_router(listings.router)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
