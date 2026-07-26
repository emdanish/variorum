from __future__ import annotations

from fastapi import APIRouter

from app.api.routes import analysis, auth, github, repositories, system, teams

api_router = APIRouter(prefix="/api/v1")
api_router.include_router(auth.router)
api_router.include_router(github.router)
api_router.include_router(repositories.router)
api_router.include_router(analysis.jobs_router)
api_router.include_router(analysis.findings_router)
api_router.include_router(analysis.risk_findings_router)
api_router.include_router(teams.router)
api_router.include_router(system.router)
