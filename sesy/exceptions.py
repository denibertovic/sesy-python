"""SESY SDK exceptions."""

from __future__ import annotations

from typing import Any


class SesyError(Exception):
    """Base exception for all SESY SDK errors."""

    def __init__(self, message: str, details: dict[str, Any] | None = None) -> None:
        self.message = message
        self.details = details or {}
        super().__init__(message)

    def __str__(self) -> str:
        if self.details:
            return f"{self.message} - {self.details}"
        return self.message


class AuthenticationError(SesyError):
    """Raised when API key is invalid or missing (HTTP 401)."""

    pass


class ValidationError(SesyError):
    """Raised when request validation fails (HTTP 400)."""

    pass


class RateLimitError(SesyError):
    """Raised when rate limit is exceeded (HTTP 429)."""

    def __init__(
        self,
        message: str,
        limit: int,
        remaining: int,
        reset_at: int,
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(message, details)
        self.limit = limit
        self.remaining = remaining
        self.reset_at = reset_at


class NotFoundError(SesyError):
    """Raised when a resource is not found (HTTP 404)."""

    pass


class SuppressionError(SesyError):
    """Raised when attempting to send to a suppressed email address."""

    pass


class NetworkError(SesyError):
    """Raised when a network error occurs (timeout, connection error, etc.)."""

    pass


class ServerError(SesyError):
    """Raised when the server returns a 5xx error."""

    pass
