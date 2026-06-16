# -*- coding: utf-8 -*-
"""
main.py — FastAPI application for the STPT admin dashboard.

Start with:
  uvicorn server.main:app --port 8080
"""

import logging
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from starlette.staticfiles import StaticFiles

from server.db import DB_PATH, init_db
from server.routes import auth, admin

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Lifespan — replaces deprecated @app.on_event("startup")
# ---------------------------------------------------------------------------

@asynccontextmanager
async def lifespan(app: FastAPI):
    db_dir = os.path.dirname(DB_PATH)
    if db_dir and not os.path.exists(db_dir):
        os.makedirs(db_dir, exist_ok=True)
    init_db()
    if DB_PATH and os.environ.get("SECRET_KEY", "change-me-in-production") == "change-me-in-production":
        logger.warning(
            "⚠️  SECRET_KEY is using the default insecure value. "
            "Set the SECRET_KEY environment variable before deployment."
        )
    yield

# ---------------------------------------------------------------------------
# App instance
# ---------------------------------------------------------------------------

app = FastAPI(title="STPT Admin API", version="1.0.0", lifespan=lifespan)

# ---------------------------------------------------------------------------
# CORS — open for now (internal tool).
# allow_credentials is intentionally omitted: Bearer tokens are sent in
# headers and do not require credentialed CORS requests.
# ---------------------------------------------------------------------------

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---------------------------------------------------------------------------
# API routers (must be registered BEFORE static mount)
# ---------------------------------------------------------------------------

app.include_router(auth.router, prefix="/api/auth", tags=["auth"])
app.include_router(admin.router, prefix="/api/admin", tags=["admin"])

# ---------------------------------------------------------------------------
# Admin UI (must be registered BEFORE static mount)
# ---------------------------------------------------------------------------

ADMIN_UI_PATH = os.path.join(os.path.dirname(__file__), "admin_ui", "index.html")


@app.get("/admin", include_in_schema=False)
@app.get("/admin/", include_in_schema=False)
async def serve_admin():
    """Serve the admin SPA placeholder."""
    return FileResponse(ADMIN_UI_PATH)


# ---------------------------------------------------------------------------
# Static files — serves the public app from the repo root
# Must be mounted LAST so the routes above take precedence.
# ---------------------------------------------------------------------------

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

app.mount("/", StaticFiles(directory=REPO_ROOT, html=True), name="static")
