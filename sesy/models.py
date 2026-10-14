"""SESY SDK data models."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any


class MessageStatus(str, Enum):
    """Status of an email message."""

    QUEUED = "queued"
    SENT = "sent"
    DELIVERED = "delivered"
    BOUNCED = "bounced"
    COMPLAINED = "complained"
    FAILED = "failed"


class SuppressionReason(str, Enum):
    """Reason for email suppression."""

    HARD_BOUNCE = "hard_bounce"
    COMPLAINT = "complaint"
    MANUAL = "manual"


@dataclass
class SendEmailResponse:
    """Response from sending an email."""

    message_id: str
    status: MessageStatus

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> SendEmailResponse:
        return cls(
            message_id=data["message_id"],
            status=MessageStatus(data["status"]),
        )


@dataclass
class Message:
    """Full message details."""

    id: str
    to_email: str
    from_email: str
    status: MessageStatus
    ses_message_id: str | None
    error_code: str | None
    error_message: str | None
    tags: dict[str, Any]
    created_at: datetime
    updated_at: datetime

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Message:
        return cls(
            id=data["id"],
            to_email=data["to_email"],
            from_email=data["from_email"],
            status=MessageStatus(data["status"]),
            ses_message_id=data.get("ses_message_id"),
            error_code=data.get("error_code"),
            error_message=data.get("error_message"),
            tags=data.get("tags", {}),
            created_at=datetime.fromisoformat(
                data["created_at"].replace("Z", "+00:00")
            ),
            updated_at=datetime.fromisoformat(
                data["updated_at"].replace("Z", "+00:00")
            ),
        )


@dataclass
class Suppression:
    """Email suppression entry."""

    id: str
    email: str
    reason: SuppressionReason
    created_at: datetime

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Suppression:
        return cls(
            id=data["id"],
            email=data["email"],
            reason=SuppressionReason(data["reason"]),
            created_at=datetime.fromisoformat(
                data["created_at"].replace("Z", "+00:00")
            ),
        )


@dataclass
class LimitInfo:
    """Information about a single rate limit."""

    limit: int
    remaining: int
    reset_at: int


@dataclass
class LimitsStatus:
    """Rate and daily limit status."""

    rate_limit: LimitInfo
    daily_limit: LimitInfo

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> LimitsStatus:
        return cls(
            rate_limit=LimitInfo(
                limit=data["rate_limit"]["limit"],
                remaining=data["rate_limit"]["remaining"],
                reset_at=data["rate_limit"]["reset_at"],
            ),
            daily_limit=LimitInfo(
                limit=data["daily_limit"]["limit"],
                remaining=data["daily_limit"]["remaining"],
                reset_at=data["daily_limit"]["reset_at"],
            ),
        )


@dataclass
class SendEmailRequest:
    """Request parameters for sending an email."""

    to: str
    template: str | None = None
    subject: str | None = None
    html: str | None = None
    text: str | None = None
    data: dict[str, Any] = field(default_factory=dict)
    tags: dict[str, Any] = field(default_factory=dict)
    idempotency_key: str | None = None
    reply_to: str | None = None

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for API request."""
        result: dict[str, Any] = {"to": self.to}

        if self.template:
            result["template"] = self.template
        if self.subject:
            result["subject"] = self.subject
        if self.html:
            result["html"] = self.html
        if self.text:
            result["text"] = self.text
        if self.data:
            result["data"] = self.data
        if self.tags:
            result["tags"] = self.tags
        if self.idempotency_key:
            result["idempotency_key"] = self.idempotency_key
        if self.reply_to:
            result["reply_to"] = self.reply_to

        return result
