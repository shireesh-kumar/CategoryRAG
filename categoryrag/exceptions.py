from __future__ import annotations

from typing import Any


class AppError(Exception):
    def __init__(self, error: str, details: dict[str, Any] | None = None) -> None:
        self.error = error
        self.details = details or {}
        super().__init__(error)


class NotFoundError(AppError):
    pass


class ValidationError(AppError):
    pass
