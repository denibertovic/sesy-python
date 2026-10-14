"""Tests for SESY SDK client."""

import pytest
from pytest_httpx import HTTPXMock

from sesy import (
    AsyncSesyClient,
    AuthenticationError,
    Message,
    MessageStatus,
    NotFoundError,
    RateLimitError,
    SendEmailResponse,
    SesyClient,
    Suppression,
    SuppressionError,
    SuppressionReason,
    ValidationError,
)


class TestSesyClient:
    """Tests for synchronous SesyClient."""

    def test_send_email_success(self, httpx_mock: HTTPXMock) -> None:
        """Test successful email sending."""
        httpx_mock.add_response(
            method="POST",
            url="https://sesy.email/api/v1/send/",
            json={"message_id": "abc-123", "status": "queued"},
            status_code=201,
        )

        client = SesyClient(api_key="test-key")
        response = client.send_email(
            to="user@example.com",
            subject="Hello",
            html="<h1>Welcome!</h1>",
        )

        assert isinstance(response, SendEmailResponse)
        assert response.message_id == "abc-123"
        assert response.status == MessageStatus.QUEUED
        client.close()

    def test_send_email_with_template(self, httpx_mock: HTTPXMock) -> None:
        """Test email sending with template."""
        httpx_mock.add_response(
            method="POST",
            url="https://sesy.email/api/v1/send/",
            json={"message_id": "def-456", "status": "queued"},
            status_code=201,
        )

        client = SesyClient(api_key="test-key")
        response = client.send_email(
            to="user@example.com",
            template="welcome",
            data={"name": "John"},
            tags={"campaign": "onboarding"},
        )

        assert response.message_id == "def-456"
        client.close()

    def test_send_email_with_idempotency_key(self, httpx_mock: HTTPXMock) -> None:
        """Test email sending with idempotency key returns existing message."""
        httpx_mock.add_response(
            method="POST",
            url="https://sesy.email/api/v1/send/",
            json={"message_id": "existing-123", "status": "sent"},
            status_code=200,
        )

        client = SesyClient(api_key="test-key")
        response = client.send_email(
            to="user@example.com",
            subject="Hello",
            text="Welcome!",
            idempotency_key="unique-key-123",
        )

        assert response.message_id == "existing-123"
        assert response.status == MessageStatus.SENT
        client.close()

    def test_send_email_authentication_error(self, httpx_mock: HTTPXMock) -> None:
        """Test authentication error handling."""
        httpx_mock.add_response(
            method="POST",
            url="https://sesy.email/api/v1/send/",
            json={"error": "Invalid authentication"},
            status_code=401,
        )

        client = SesyClient(api_key="invalid-key")
        with pytest.raises(AuthenticationError):
            client.send_email(to="user@example.com", subject="Test", text="Test")
        client.close()

    def test_send_email_validation_error(self, httpx_mock: HTTPXMock) -> None:
        """Test validation error handling."""
        httpx_mock.add_response(
            method="POST",
            url="https://sesy.email/api/v1/send/",
            json={"error": "Either 'template' or 'subject' with content required"},
            status_code=400,
        )

        client = SesyClient(api_key="test-key")
        with pytest.raises(ValidationError):
            client.send_email(to="user@example.com")
        client.close()

    def test_send_email_suppression_error(self, httpx_mock: HTTPXMock) -> None:
        """Test suppression error handling."""
        httpx_mock.add_response(
            method="POST",
            url="https://sesy.email/api/v1/send/",
            json={"error": "Email address is suppressed"},
            status_code=400,
        )

        client = SesyClient(api_key="test-key")
        with pytest.raises(SuppressionError):
            client.send_email(to="suppressed@example.com", subject="Test", text="Test")
        client.close()

    def test_send_email_rate_limit_error(self, httpx_mock: HTTPXMock) -> None:
        """Test rate limit error handling."""
        httpx_mock.add_response(
            method="POST",
            url="https://sesy.email/api/v1/send/",
            json={
                "error": "Rate limit exceeded",
                "limit": 60,
                "remaining": 0,
                "reset_at": 1700000000,
            },
            status_code=429,
        )

        client = SesyClient(api_key="test-key")
        with pytest.raises(RateLimitError) as exc_info:
            client.send_email(to="user@example.com", subject="Test", text="Test")

        assert exc_info.value.limit == 60
        assert exc_info.value.remaining == 0
        assert exc_info.value.reset_at == 1700000000
        client.close()

    def test_get_message_success(self, httpx_mock: HTTPXMock) -> None:
        """Test getting message details."""
        httpx_mock.add_response(
            method="GET",
            url="https://sesy.email/api/v1/messages/abc-123/",
            json={
                "id": "abc-123",
                "to_email": "user@example.com",
                "from_email": "noreply@example.com",
                "status": "delivered",
                "ses_message_id": "ses-abc-123",
                "error_code": None,
                "error_message": None,
                "tags": {"campaign": "test"},
                "created_at": "2024-01-01T00:00:00Z",
                "updated_at": "2024-01-01T00:01:00Z",
            },
        )

        client = SesyClient(api_key="test-key")
        message = client.get_message("abc-123")

        assert isinstance(message, Message)
        assert message.id == "abc-123"
        assert message.status == MessageStatus.DELIVERED
        assert message.ses_message_id == "ses-abc-123"
        client.close()

    def test_get_message_not_found(self, httpx_mock: HTTPXMock) -> None:
        """Test message not found error."""
        httpx_mock.add_response(
            method="GET",
            url="https://sesy.email/api/v1/messages/not-found/",
            json={"detail": "Not found."},
            status_code=404,
        )

        client = SesyClient(api_key="test-key")
        with pytest.raises(NotFoundError):
            client.get_message("not-found")
        client.close()

    def test_list_suppressions(self, httpx_mock: HTTPXMock) -> None:
        """Test listing suppressions."""
        httpx_mock.add_response(
            method="GET",
            url="https://sesy.email/api/v1/suppressions/",
            json=[
                {
                    "id": "sup-1",
                    "email": "bounced@example.com",
                    "reason": "hard_bounce",
                    "created_at": "2024-01-01T00:00:00Z",
                },
                {
                    "id": "sup-2",
                    "email": "complained@example.com",
                    "reason": "complaint",
                    "created_at": "2024-01-02T00:00:00Z",
                },
            ],
        )

        client = SesyClient(api_key="test-key")
        suppressions = client.list_suppressions()

        assert len(suppressions) == 2
        assert suppressions[0].email == "bounced@example.com"
        assert suppressions[0].reason == SuppressionReason.HARD_BOUNCE
        assert suppressions[1].reason == SuppressionReason.COMPLAINT
        client.close()

    def test_add_suppression(self, httpx_mock: HTTPXMock) -> None:
        """Test adding a suppression."""
        httpx_mock.add_response(
            method="POST",
            url="https://sesy.email/api/v1/suppressions/",
            json={
                "id": "sup-new",
                "email": "manual@example.com",
                "reason": "manual",
                "created_at": "2024-01-03T00:00:00Z",
            },
            status_code=201,
        )

        client = SesyClient(api_key="test-key")
        suppression = client.add_suppression(
            email="manual@example.com",
            reason=SuppressionReason.MANUAL,
        )

        assert isinstance(suppression, Suppression)
        assert suppression.email == "manual@example.com"
        assert suppression.reason == SuppressionReason.MANUAL
        client.close()

    def test_get_limits(self, httpx_mock: HTTPXMock) -> None:
        """Test getting rate limits."""
        httpx_mock.add_response(
            method="GET",
            url="https://sesy.email/api/v1/limits/",
            json={
                "rate_limit": {
                    "limit": 60,
                    "remaining": 55,
                    "reset_at": 1700000060,
                },
                "daily_limit": {
                    "limit": 100,
                    "remaining": 90,
                    "reset_at": 1700086400,
                },
            },
        )

        client = SesyClient(api_key="test-key")
        limits = client.get_limits()

        assert limits.rate_limit.limit == 60
        assert limits.rate_limit.remaining == 55
        assert limits.daily_limit.limit == 100
        assert limits.daily_limit.remaining == 90
        client.close()

    def test_context_manager(self, httpx_mock: HTTPXMock) -> None:
        """Test using client as context manager."""
        httpx_mock.add_response(
            method="GET",
            url="https://sesy.email/api/v1/limits/",
            json={
                "rate_limit": {"limit": 60, "remaining": 60, "reset_at": 0},
                "daily_limit": {"limit": 100, "remaining": 100, "reset_at": 0},
            },
        )

        with SesyClient(api_key="test-key") as client:
            limits = client.get_limits()
            assert limits.rate_limit.limit == 60

    def test_custom_base_url(self, httpx_mock: HTTPXMock) -> None:
        """Test using custom base URL."""
        httpx_mock.add_response(
            method="GET",
            url="https://custom.example.com/api/v1/limits/",
            json={
                "rate_limit": {"limit": 60, "remaining": 60, "reset_at": 0},
                "daily_limit": {"limit": 100, "remaining": 100, "reset_at": 0},
            },
        )

        client = SesyClient(
            api_key="test-key",
            base_url="https://custom.example.com",
        )
        limits = client.get_limits()
        assert limits is not None
        client.close()


class TestAsyncSesyClient:
    """Tests for async SesyClient."""

    @pytest.mark.asyncio
    async def test_send_email_success(self, httpx_mock: HTTPXMock) -> None:
        """Test successful async email sending."""
        httpx_mock.add_response(
            method="POST",
            url="https://sesy.email/api/v1/send/",
            json={"message_id": "async-123", "status": "queued"},
            status_code=201,
        )

        async with AsyncSesyClient(api_key="test-key") as client:
            response = await client.send_email(
                to="user@example.com",
                subject="Hello",
                html="<h1>Welcome!</h1>",
            )

        assert response.message_id == "async-123"
        assert response.status == MessageStatus.QUEUED

    @pytest.mark.asyncio
    async def test_get_message(self, httpx_mock: HTTPXMock) -> None:
        """Test async get message."""
        httpx_mock.add_response(
            method="GET",
            url="https://sesy.email/api/v1/messages/async-123/",
            json={
                "id": "async-123",
                "to_email": "user@example.com",
                "from_email": "noreply@example.com",
                "status": "sent",
                "ses_message_id": None,
                "error_code": None,
                "error_message": None,
                "tags": {},
                "created_at": "2024-01-01T00:00:00Z",
                "updated_at": "2024-01-01T00:00:00Z",
            },
        )

        async with AsyncSesyClient(api_key="test-key") as client:
            message = await client.get_message("async-123")

        assert message.id == "async-123"
        assert message.status == MessageStatus.SENT

    @pytest.mark.asyncio
    async def test_list_suppressions(self, httpx_mock: HTTPXMock) -> None:
        """Test async list suppressions."""
        httpx_mock.add_response(
            method="GET",
            url="https://sesy.email/api/v1/suppressions/",
            json=[
                {
                    "id": "sup-1",
                    "email": "test@example.com",
                    "reason": "manual",
                    "created_at": "2024-01-01T00:00:00Z",
                },
            ],
        )

        async with AsyncSesyClient(api_key="test-key") as client:
            suppressions = await client.list_suppressions()

        assert len(suppressions) == 1

    @pytest.mark.asyncio
    async def test_add_suppression(self, httpx_mock: HTTPXMock) -> None:
        """Test async add suppression."""
        httpx_mock.add_response(
            method="POST",
            url="https://sesy.email/api/v1/suppressions/",
            json={
                "id": "sup-new",
                "email": "new@example.com",
                "reason": "manual",
                "created_at": "2024-01-01T00:00:00Z",
            },
            status_code=201,
        )

        async with AsyncSesyClient(api_key="test-key") as client:
            suppression = await client.add_suppression("new@example.com")

        assert suppression.email == "new@example.com"

    @pytest.mark.asyncio
    async def test_get_limits(self, httpx_mock: HTTPXMock) -> None:
        """Test async get limits."""
        httpx_mock.add_response(
            method="GET",
            url="https://sesy.email/api/v1/limits/",
            json={
                "rate_limit": {"limit": 60, "remaining": 60, "reset_at": 0},
                "daily_limit": {"limit": 100, "remaining": 100, "reset_at": 0},
            },
        )

        async with AsyncSesyClient(api_key="test-key") as client:
            limits = await client.get_limits()

        assert limits.rate_limit.limit == 60

    @pytest.mark.asyncio
    async def test_authentication_error(self, httpx_mock: HTTPXMock) -> None:
        """Test async authentication error."""
        httpx_mock.add_response(
            method="GET",
            url="https://sesy.email/api/v1/limits/",
            json={"error": "Invalid authentication"},
            status_code=401,
        )

        async with AsyncSesyClient(api_key="bad-key") as client:
            with pytest.raises(AuthenticationError):
                await client.get_limits()
