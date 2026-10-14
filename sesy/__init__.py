"""SESY Python SDK - Client library for the SESY email service."""

from .client import AsyncSesyClient, SesyClient
from .exceptions import (
    AuthenticationError,
    NetworkError,
    NotFoundError,
    RateLimitError,
    ServerError,
    SesyError,
    SuppressionError,
    ValidationError,
)
from .models import (
    LimitInfo,
    LimitsStatus,
    Message,
    MessageStatus,
    SendEmailRequest,
    SendEmailResponse,
    Suppression,
    SuppressionReason,
)

__version__ = "0.1.0"

__all__ = [
    # Clients
    "SesyClient",
    "AsyncSesyClient",
    # Models
    "Message",
    "MessageStatus",
    "Suppression",
    "SuppressionReason",
    "SendEmailRequest",
    "SendEmailResponse",
    "LimitInfo",
    "LimitsStatus",
    # Exceptions
    "SesyError",
    "AuthenticationError",
    "ValidationError",
    "RateLimitError",
    "NotFoundError",
    "SuppressionError",
    "NetworkError",
    "ServerError",
]
