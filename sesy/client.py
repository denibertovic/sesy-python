"""SESY SDK client implementations."""

from __future__ import annotations

from typing import Any

import httpx

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
    LimitsStatus,
    Message,
    SendEmailRequest,
    SendEmailResponse,
    Suppression,
    SuppressionReason,
)

DEFAULT_BASE_URL = "https://sesy.email"
DEFAULT_TIMEOUT = 30.0


class SesyClient:
    """Synchronous SESY API client.

    Example:
        >>> client = SesyClient(api_key="your-api-key")
        >>> response = client.send_email(
        ...     to="user@example.com",
        ...     subject="Hello",
        ...     html="<h1>Welcome!</h1>",
        ... )
        >>> print(response.message_id)

    Can also be used as a context manager:
        >>> with SesyClient(api_key="your-api-key") as client:
        ...     response = client.send_email(...)
    """

    def __init__(
        self,
        api_key: str,
        base_url: str = DEFAULT_BASE_URL,
        timeout: float = DEFAULT_TIMEOUT,
    ) -> None:
        """Initialize the SESY client.

        Args:
            api_key: Your SESY API key.
            base_url: Base URL for the SESY API (default: https://sesy.email).
            timeout: Request timeout in seconds (default: 30).
        """
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self._client: httpx.Client | None = None

    @property
    def client(self) -> httpx.Client:
        """Get or create the HTTP client."""
        if self._client is None:
            self._client = httpx.Client(
                base_url=self.base_url,
                headers={"X-API-Key": self.api_key},
                timeout=self.timeout,
            )
        return self._client

    def __enter__(self) -> SesyClient:
        return self

    def __exit__(self, *args: Any) -> None:
        self.close()

    def close(self) -> None:
        """Close the HTTP client."""
        if self._client is not None:
            self._client.close()
            self._client = None

    def _handle_response(self, response: httpx.Response) -> dict[str, Any]:
        """Handle HTTP response and raise appropriate exceptions."""
        if response.status_code == 401:
            raise AuthenticationError("Invalid API key")

        if response.status_code == 404:
            raise NotFoundError("Resource not found")

        if response.status_code == 429:
            data = response.json()
            raise RateLimitError(
                message=data.get("error", "Rate limit exceeded"),
                limit=data.get("limit", 0),
                remaining=data.get("remaining", 0),
                reset_at=data.get("reset_at", 0),
            )

        if response.status_code == 400:
            data = response.json()
            error = data.get("error", "")
            if "suppressed" in error.lower():
                raise SuppressionError(error)
            raise ValidationError(error, details=data)

        if response.status_code >= 500:
            raise ServerError(f"Server error: {response.status_code}")

        if response.status_code >= 400:
            raise SesyError(f"Request failed: {response.status_code}")

        return response.json()

    def send_email(
        self,
        to: str,
        *,
        template: str | None = None,
        subject: str | None = None,
        html: str | None = None,
        text: str | None = None,
        data: dict[str, Any] | None = None,
        tags: dict[str, Any] | None = None,
        idempotency_key: str | None = None,
        reply_to: str | None = None,
    ) -> SendEmailResponse:
        """Send an email.

        Either `template` OR both `subject` and (`html` or `text`) must be provided.

        Args:
            to: Recipient email address.
            template: Name of the template to use.
            subject: Email subject (required if not using template).
            html: HTML body content.
            text: Plain text body content.
            data: Template data for variable substitution.
            tags: Custom tags for tracking.
            idempotency_key: Unique key to prevent duplicate sends.
            reply_to: Email address for the Reply-To header.

        Returns:
            SendEmailResponse with message_id and status.

        Raises:
            ValidationError: If required parameters are missing.
            SuppressionError: If recipient is suppressed.
            RateLimitError: If rate limit is exceeded.
            AuthenticationError: If API key is invalid.
        """
        request = SendEmailRequest(
            to=to,
            template=template,
            subject=subject,
            html=html,
            text=text,
            data=data or {},
            tags=tags or {},
            idempotency_key=idempotency_key,
            reply_to=reply_to,
        )

        try:
            response = self.client.post("/api/v1/send/", json=request.to_dict())
            data = self._handle_response(response)
            return SendEmailResponse.from_dict(data)
        except httpx.TimeoutException as e:
            raise NetworkError(f"Request timed out: {e}") from e
        except httpx.RequestError as e:
            raise NetworkError(f"Network error: {e}") from e

    def get_message(self, message_id: str) -> Message:
        """Get message details by ID.

        Args:
            message_id: UUID of the message.

        Returns:
            Message with full details.

        Raises:
            NotFoundError: If message is not found.
            AuthenticationError: If API key is invalid.
        """
        try:
            response = self.client.get(f"/api/v1/messages/{message_id}/")
            data = self._handle_response(response)
            return Message.from_dict(data)
        except httpx.TimeoutException as e:
            raise NetworkError(f"Request timed out: {e}") from e
        except httpx.RequestError as e:
            raise NetworkError(f"Network error: {e}") from e

    def list_suppressions(self) -> list[Suppression]:
        """List all suppressed email addresses.

        Returns:
            List of Suppression entries.

        Raises:
            AuthenticationError: If API key is invalid.
        """
        try:
            response = self.client.get("/api/v1/suppressions/")
            data = self._handle_response(response)
            return [Suppression.from_dict(item) for item in data]
        except httpx.TimeoutException as e:
            raise NetworkError(f"Request timed out: {e}") from e
        except httpx.RequestError as e:
            raise NetworkError(f"Network error: {e}") from e

    def add_suppression(
        self,
        email: str,
        reason: SuppressionReason = SuppressionReason.MANUAL,
    ) -> Suppression:
        """Add an email to the suppression list.

        Args:
            email: Email address to suppress.
            reason: Reason for suppression (default: manual).

        Returns:
            Created Suppression entry.

        Raises:
            ValidationError: If email is invalid.
            AuthenticationError: If API key is invalid.
        """
        try:
            response = self.client.post(
                "/api/v1/suppressions/",
                json={"email": email, "reason": reason.value},
            )
            data = self._handle_response(response)
            return Suppression.from_dict(data)
        except httpx.TimeoutException as e:
            raise NetworkError(f"Request timed out: {e}") from e
        except httpx.RequestError as e:
            raise NetworkError(f"Network error: {e}") from e

    def get_limits(self) -> LimitsStatus:
        """Get current rate limit and daily limit status.

        Returns:
            LimitsStatus with rate and daily limit info.

        Raises:
            AuthenticationError: If API key is invalid.
        """
        try:
            response = self.client.get("/api/v1/limits/")
            data = self._handle_response(response)
            return LimitsStatus.from_dict(data)
        except httpx.TimeoutException as e:
            raise NetworkError(f"Request timed out: {e}") from e
        except httpx.RequestError as e:
            raise NetworkError(f"Network error: {e}") from e


class AsyncSesyClient:
    """Asynchronous SESY API client.

    Example:
        >>> async with AsyncSesyClient(api_key="your-api-key") as client:
        ...     response = await client.send_email(
        ...         to="user@example.com",
        ...         subject="Hello",
        ...         html="<h1>Welcome!</h1>",
        ...     )
        ...     print(response.message_id)
    """

    def __init__(
        self,
        api_key: str,
        base_url: str = DEFAULT_BASE_URL,
        timeout: float = DEFAULT_TIMEOUT,
    ) -> None:
        """Initialize the async SESY client.

        Args:
            api_key: Your SESY API key.
            base_url: Base URL for the SESY API (default: https://sesy.email).
            timeout: Request timeout in seconds (default: 30).
        """
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self._client: httpx.AsyncClient | None = None

    @property
    def client(self) -> httpx.AsyncClient:
        """Get or create the async HTTP client."""
        if self._client is None:
            self._client = httpx.AsyncClient(
                base_url=self.base_url,
                headers={"X-API-Key": self.api_key},
                timeout=self.timeout,
            )
        return self._client

    async def __aenter__(self) -> AsyncSesyClient:
        return self

    async def __aexit__(self, *args: Any) -> None:
        await self.close()

    async def close(self) -> None:
        """Close the HTTP client."""
        if self._client is not None:
            await self._client.aclose()
            self._client = None

    def _handle_response(self, response: httpx.Response) -> dict[str, Any]:
        """Handle HTTP response and raise appropriate exceptions."""
        if response.status_code == 401:
            raise AuthenticationError("Invalid API key")

        if response.status_code == 404:
            raise NotFoundError("Resource not found")

        if response.status_code == 429:
            data = response.json()
            raise RateLimitError(
                message=data.get("error", "Rate limit exceeded"),
                limit=data.get("limit", 0),
                remaining=data.get("remaining", 0),
                reset_at=data.get("reset_at", 0),
            )

        if response.status_code == 400:
            data = response.json()
            error = data.get("error", "")
            if "suppressed" in error.lower():
                raise SuppressionError(error)
            raise ValidationError(error, details=data)

        if response.status_code >= 500:
            raise ServerError(f"Server error: {response.status_code}")

        if response.status_code >= 400:
            raise SesyError(f"Request failed: {response.status_code}")

        return response.json()

    async def send_email(
        self,
        to: str,
        *,
        template: str | None = None,
        subject: str | None = None,
        html: str | None = None,
        text: str | None = None,
        data: dict[str, Any] | None = None,
        tags: dict[str, Any] | None = None,
        idempotency_key: str | None = None,
        reply_to: str | None = None,
    ) -> SendEmailResponse:
        """Send an email asynchronously.

        Either `template` OR both `subject` and (`html` or `text`) must be provided.

        Args:
            to: Recipient email address.
            template: Name of the template to use.
            subject: Email subject (required if not using template).
            html: HTML body content.
            text: Plain text body content.
            data: Template data for variable substitution.
            tags: Custom tags for tracking.
            idempotency_key: Unique key to prevent duplicate sends.
            reply_to: Email address for the Reply-To header.

        Returns:
            SendEmailResponse with message_id and status.
        """
        request = SendEmailRequest(
            to=to,
            template=template,
            subject=subject,
            html=html,
            text=text,
            data=data or {},
            tags=tags or {},
            idempotency_key=idempotency_key,
            reply_to=reply_to,
        )

        try:
            response = await self.client.post("/api/v1/send/", json=request.to_dict())
            data = self._handle_response(response)
            return SendEmailResponse.from_dict(data)
        except httpx.TimeoutException as e:
            raise NetworkError(f"Request timed out: {e}") from e
        except httpx.RequestError as e:
            raise NetworkError(f"Network error: {e}") from e

    async def get_message(self, message_id: str) -> Message:
        """Get message details by ID asynchronously."""
        try:
            response = await self.client.get(f"/api/v1/messages/{message_id}/")
            data = self._handle_response(response)
            return Message.from_dict(data)
        except httpx.TimeoutException as e:
            raise NetworkError(f"Request timed out: {e}") from e
        except httpx.RequestError as e:
            raise NetworkError(f"Network error: {e}") from e

    async def list_suppressions(self) -> list[Suppression]:
        """List all suppressed email addresses asynchronously."""
        try:
            response = await self.client.get("/api/v1/suppressions/")
            data = self._handle_response(response)
            return [Suppression.from_dict(item) for item in data]
        except httpx.TimeoutException as e:
            raise NetworkError(f"Request timed out: {e}") from e
        except httpx.RequestError as e:
            raise NetworkError(f"Network error: {e}") from e

    async def add_suppression(
        self,
        email: str,
        reason: SuppressionReason = SuppressionReason.MANUAL,
    ) -> Suppression:
        """Add an email to the suppression list asynchronously."""
        try:
            response = await self.client.post(
                "/api/v1/suppressions/",
                json={"email": email, "reason": reason.value},
            )
            data = self._handle_response(response)
            return Suppression.from_dict(data)
        except httpx.TimeoutException as e:
            raise NetworkError(f"Request timed out: {e}") from e
        except httpx.RequestError as e:
            raise NetworkError(f"Network error: {e}") from e

    async def get_limits(self) -> LimitsStatus:
        """Get current rate limit and daily limit status asynchronously."""
        try:
            response = await self.client.get("/api/v1/limits/")
            data = self._handle_response(response)
            return LimitsStatus.from_dict(data)
        except httpx.TimeoutException as e:
            raise NetworkError(f"Request timed out: {e}") from e
        except httpx.RequestError as e:
            raise NetworkError(f"Network error: {e}") from e
