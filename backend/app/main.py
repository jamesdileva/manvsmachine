"""FastAPI application entry point."""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.v1 import api_router
from app.core.config import settings
from app.core.exceptions import AppError, error_detail
from app.core.state import state_store
from app.db.connection import close_db, init_db


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    """Migrate the schema and reset ephemeral state on startup; release on shutdown."""
    await init_db()
    state_store.clear()
    yield
    await close_db()


app = FastAPI(
    title="Man vs. Machine",
    version="0.1.0",
    description="Micro-challenge social deduction game — local web dashboard.",
    lifespan=lifespan,
)

app.include_router(api_router)

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


@app.get("/")
async def health_check() -> dict[str, str]:
    """Health check endpoint."""
    return {"status": "ok"}
