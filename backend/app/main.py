"""FastAPI application entry point."""

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.core.config import settings

app = FastAPI(
    title="Man vs. Machine",
    version="0.1.0",
    description="Micro-challenge social deduction game — local web dashboard.",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Catch-all handler so unexpected errors return JSON instead of an HTML traceback."""
    return JSONResponse(status_code=500, content={"detail": "Internal server error"})


@app.get("/")
async def health_check() -> dict[str, str]:
    """Health check endpoint."""
    return {"status": "ok"}
