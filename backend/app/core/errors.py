"""Application-level error types and FastAPI exception handlers.

All errors inherit from ``AppError``. Each one carries a stable ``code`` string
that the UI uses to render actionable failure states (e.g. distinguishing
authentication failures from remote-path failures during a connection test).
"""
from __future__ import annotations

from typing import Any


class AppError(Exception):
    code: str = "app_error"
    http_status: int = 400

    def __init__(self, message: str, *, details: dict[str, Any] | None = None) -> None:
        super().__init__(message)
        self.message = message
        self.details = details or {}

    def to_payload(self) -> dict[str, Any]:
        return {"code": self.code, "message": self.message, "details": self.details}


class NotFoundError(AppError):
    code = "not_found"
    http_status = 404


class ValidationError(AppError):
    code = "validation_error"
    http_status = 422


class ConflictError(AppError):
    code = "conflict"
    http_status = 409


class ConnectionTestError(AppError):
    code = "connection_test_failed"
    http_status = 200  # tests return 200 with structured detail, not a hard failure

    def __init__(
        self,
        message: str,
        *,
        stage: str,
        detail: str | None = None,
    ) -> None:
        super().__init__(message, details={"stage": stage, "detail": detail})
        self.stage = stage
        self.stage_detail = detail


class SyncError(AppError):
    code = "sync_failed"
    http_status = 200  # partial syncs are returned, not raised as 5xx


class ProviderError(AppError):
    code = "provider_error"
    http_status = 502
