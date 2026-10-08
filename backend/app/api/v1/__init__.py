"""API layer: versioned routers."""

from fastapi import APIRouter

from app.api.v1 import challenges, leaderboard, session, user, voting

api_router = APIRouter(prefix="/api/v1")
api_router.include_router(user.router)
api_router.include_router(challenges.router)
api_router.include_router(session.router)
api_router.include_router(voting.router)
api_router.include_router(leaderboard.router)
