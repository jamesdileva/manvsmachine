"""FastAPI application entry point."""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from sqlalchemy.ext.asyncio import async_sessionmaker

from app.api.v1 import api_router
from app.core.config import settings
from app.core.exceptions import AppError, error_detail
from app.core.state import state_store
from app.db.connection import close_db, get_engine, init_db
from app.services.challenge_service import sync_library_to_db
from app.websocket.handlers import session_socket

# The Vite build output (Sprint 27): served on the same port as the API so a
# release runs on one port with no Docker.
FRONTEND_DIST_DIR = Path(__file__).resolve().parents[2] / "frontend" / "dist"

# Path prefixes the SPA fallback must never claim: they belong to the API/docs.
_RESERVED_PREFIXES = ("api", "ws", "docs", "redoc", "openapi.json", "health")


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    """Migrate the schema, sync the challenge library, reset ephemeral state; release on shutdown."""
    await init_db()
    state_store.clear()
    async with async_sessionmaker(get_engine(), expire_on_commit=False)() as db:
        await sync_library_to_db(db)
    yield
    await close_db()


app = FastAPI(
    title="Man vs. Machine",
    version="0.1.0",
    description="Micro-challenge social deduction game — local web dashboard.",
    lifespan=lifespan,
)

app.include_router(api_router)
app.add_api_websocket_route("/ws/session/{session_id}", session_socket)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(AppError)
async def app_error_handler(request: Request, exc: AppError) -> JSONResponse:
    """Map domain errors (auth, conflicts, not-found) to JSON responses."""
    return JSONResponse(status_code=exc.status_code, content=error_detail(exc))


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Catch-all handler so unexpected errors return JSON instead of an HTML traceback."""
    return JSONResponse(status_code=500, content={"detail": "Internal server error"})


@app.get("/health")
async def health_check() -> dict[str, str]:
    """Health check endpoint."""
    return {"status": "ok"}


# ---------------------------------------------------------------------------
# Release mode: serve the built frontend on the same port (Sprint 27)

# Registered last, so every API/docs/websocket route above wins the match.
# Both handlers read the directory per request (no import-time snapshot), so
# tests — and a rebuild while the server runs — are picked up.
_RESERVED_PREFIXES = ("api", "ws", "docs", "redoc", "openapi.json", "health")


@app.get("/{full_path:path}", include_in_schema=False)
async def serve_spa(full_path: str) -> FileResponse:
    """Serve a build file, or index.html for client-side routes.

    Never claimed for `api`/`ws`/`docs`/`health` prefixes — those belong to the
    API, so a typo'd API path returns a JSON 404 instead of the shell. Without a
    build (dev mode) this is a plain 404 and the API is untouched.
    """
    if FRONTEND_DIST_DIR.name == "dist" and not FRONTEND_DIST_DIR.is_dir():
        raise HTTPException(status_code=404, detail="frontend build not found")

    first = full_path.split("/", 1)[0] if full_path else ""
    if first in _RESERVED_PREFIXES:
        raise HTTPException(status_code=404, detail="not found")

    candidate = FRONTEND_DIST_DIR / full_path
    if candidate.is_file():
        return FileResponse(candidate)
    if first == "assets":
        # A missing bundle is a broken build, not a client-side route.
        raise HTTPException(status_code=404, detail="asset not found")

    index = FRONTEND_DIST_DIR / "index.html"
    if not index.is_file():
        raise HTTPException(status_code=404, detail="frontend build not found")
    return FileResponse(index)
