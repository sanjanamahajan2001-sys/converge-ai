"""Abstract base definitions and data transfer objects for email delivery."""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional


@dataclass
class EmailMessage:
    """Represents an outgoing email message."""

    to: List[str]
    subject: str
    html_body: str
    text_body: Optional[str] = None
    sender_address: Optional[str] = None
    sender_name: Optional[str] = None
    reply_to: Optional[str] = None
    cc: Optional[List[str]] = None
    bcc: Optional[List[str]] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class EmailDispatchResult:
    """Result of an attempted email dispatch."""

    success: bool
    message_id: Optional[str] = None
    error: Optional[str] = None
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


class EmailServiceBase(ABC):
    """Abstract interface for email delivery services."""

    @abstractmethod
    async def send_email(self, message: EmailMessage) -> EmailDispatchResult:
        """Asynchronously send an email message."""
        raise NotImplementedError
