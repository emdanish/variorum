from __future__ import annotations

from fastapi import APIRouter

from app.api.routes import github, repositories

api_router = APIRouter(prefix="/api/v1")
api_router.include_router(github.router)
api_router.include_router(repositories.router)
