from __future__ import annotations

from pydantic import BaseModel


class HealthResponse(BaseModel):
    status: str
    app: str
    environment: str
    ai_available: bool
    ai_providers: list[str]


class InstallUrlResponse(BaseModel):
    install_url: str


class ErrorDetail(BaseModel):
    code: str
    message: str
    details: dict | None = None


class ErrorEnvelope(BaseModel):
    error: ErrorDetail
