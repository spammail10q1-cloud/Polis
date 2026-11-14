"""POLIS API entry point."""

from __future__ import annotations

import logging
import time
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api import assistant, auth, causal, genetics, labs, medications, models, overview, privacy, profile, simulations, twin, wearables
from app.core.config import settings
from app.core.db import Base, SessionLocal, engine
from app.models import ModelVersion  # noqa: F401 - ensure all models are registered
from app.services.seed import seed_all

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")
logger = logging.getLogger("polis")


@asynccontextmanager
async def lifespan(_app: FastAPI):
    if settings.is_production:
        weak = (
            len(settings.secret_key) < 32
            or settings.secret_key.startswith("polis-development")
            or settings.secret_key.lower().startswith("change-me")
            or "development-only" in settings.secret_key.lower()
        )
        if weak:
            raise RuntimeError(
                "SECRET_KEY must be set to a strong, unique value (at least 32 chars) in production."
            )
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        seed_all(db)
        logger.info("POLIS reference data and demo profile are ready")
    except Exception:
        db.rollback()
        logger.exception("Seeding failed")
        raise
    finally:
        db.close()
    yield


app = FastAPI(
    title="POLIS API",
    version="0.1.0",
    description=(
        "Privacy-preserving personal digital twin research platform. Experimental; not a medical device. "
        "Demonstration data are synthetic."
    ),
    lifespan=lifespan,
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    openapi_url="/api/openapi.json",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def csrf_origin_guard(request: Request, call_next):
    """Reject cross-site cookie-authenticated mutations with a foreign Origin.

    SameSite=Lax is the primary CSRF defence; origin checking is defence in
    depth. Bearer-token API clients are unaffected. Requests without an Origin
    header (server-to-server, CLI) are allowed.
    """
    if request.method in {"POST", "PUT", "PATCH", "DELETE"} and request.cookies.get(settings.cookie_name):
        origin = request.headers.get("origin")
        if origin:
            normalized = origin.rstrip("/")
            allowed = {item.rstrip("/") for item in settings.cors_origin_list}
            if normalized not in allowed:
                return JSONResponse(
                    status_code=403,
                    content={"detail": "Cross-site request rejected. Configure CORS_ORIGINS for your deployed origin."},
                )
    return await call_next(request)


@app.middleware("http")
async def security_headers(request: Request, call_next):
    content_length = request.headers.get("content-length")
    if content_length and content_length.isdigit() and int(content_length) > 30_000_000:
        return JSONResponse(status_code=413, content={"detail": "Request body exceeds the 30 MB limit."})
    started = time.perf_counter()
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"
    response.headers["Cache-Control"] = "no-store"
    response.headers["X-Process-Time-Ms"] = f"{(time.perf_counter() - started) * 1000:.1f}"
    if settings.is_production and (request.url.scheme == "https" or request.headers.get("x-forwarded-proto") == "https"):
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
    return response


@app.get("/health", tags=["system"])
def health() -> dict:
    return {"status": "ok", "service": "polis-api", "version": "0.1.0"}


@app.get("/api/v1", tags=["system"])
def api_root() -> dict:
    return {
        "name": "POLIS API",
        "version": "0.1.0",
        "status": "experimental",
        "notice": "Not a medical device. Demonstration data are synthetic. No clinical decisions.",
        "documentation": "/api/docs",
    }


for router_module in [
    auth,
    profile,
    labs,
    genetics,
    medications,
    twin,
    simulations,
    assistant,
    wearables,
    privacy,
    overview,
    models,
    causal,
]:
    app.include_router(router_module.router, prefix=settings.api_prefix)
