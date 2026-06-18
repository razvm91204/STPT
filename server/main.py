# -*- coding: utf-8 -*-
"""
main.py — FastAPI application for the STPT admin dashboard.

Start with:
  uvicorn server.main:app --port 8080
"""

import logging
import os
from contextlib import asynccontextmanager

import sentry_sdk
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from starlette.staticfiles import StaticFiles

from server.db import DB_PATH, init_db
from server.limiter import limiter
from server.routes import auth, admin

logger = logging.getLogger(__name__)

# ── Sentry (no-op when SENTRY_DSN is absent) ─────────────────────────────────

_sentry_dsn = os.environ.get("SENTRY_DSN")
if _sentry_dsn:
    sentry_sdk.init(dsn=_sentry_dsn, traces_sample_rate=0.1)

# ── Lifespan ──────────────────────────────────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI):
    db_dir = os.path.dirname(DB_PATH)
    if db_dir and not os.path.exists(db_dir):
        os.makedirs(db_dir, exist_ok=True)
    init_db()
    yield

# ── App instance ──────────────────────────────────────────────────────────────

app = FastAPI(title="STPT Admin API", version="1.0.0", lifespan=lifespan)

# ── Rate limiter ──────────────────────────────────────────────────────────────

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# ── CORS ──────────────────────────────────────────────────────────────────────
# Restricted to the production origin. For local dev, set DEV_CORS_ORIGIN=http://localhost:8080

_cors_origins = ["https://stpt-admin.fly.dev"]
_dev_origin = os.environ.get("DEV_CORS_ORIGIN")
if _dev_origin:
    _cors_origins.append(_dev_origin)

app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── API routers (must be registered BEFORE static mount) ─────────────────────

app.include_router(auth.router, prefix="/api/auth", tags=["auth"])
app.include_router(admin.router, prefix="/api/admin", tags=["admin"])

# ── Health check ──────────────────────────────────────────────────────────────

@app.get("/health", include_in_schema=False)
async def health():
    return JSONResponse({"status": "ok"})

# ── Admin UI (must be registered BEFORE static mount) ────────────────────────

ADMIN_UI_PATH = os.path.join(os.path.dirname(__file__), "admin_ui", "index.html")


@app.get("/admin", include_in_schema=False)
@app.get("/admin/", include_in_schema=False)
async def serve_admin():
    """Serve the admin SPA placeholder."""
    return FileResponse(ADMIN_UI_PATH)


# ── Static files — serves only the public/ subdirectory, not the repo root.
# Must be mounted LAST so the routes above take precedence.

PUBLIC_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "public")

app.mount("/", StaticFiles(directory=PUBLIC_DIR, html=True), name="static")
