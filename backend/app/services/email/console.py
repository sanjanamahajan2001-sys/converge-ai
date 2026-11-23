"""Console and mock email service for testing and development environments."""

import logging
from typing import List

from app.services.email.base import EmailDispatchResult, EmailMessage, EmailServiceBase

logger = logging.getLogger(__name__)


class ConsoleEmailService(EmailServiceBase):
    """Logs outgoing emails and keeps an in-memory history for test assertions."""

    def __init__(self) -> None:
        self.sent_messages: List[EmailMessage] = []

    async def send_email(self, message: EmailMessage) -> EmailDispatchResult:
        """Record email in memory and log output to console."""
        self.sent_messages.append(message)
        sender = f"{message.sender_name or 'System'} <{message.sender_address or 'default'}>"
        recipients = ", ".join(message.to)

        logger.info(
            "[EMAIL CONSOLE DISPATCH]\nFrom: %s\nTo: %s\nSubject: %s\nBody Length: %d chars",
            sender,
            recipients,
            message.subject,
            len(message.html_body),
        )

        simulated_id = f"sim-{len(self.sent_messages)}-{hash(message.subject)}"
        return EmailDispatchResult(
            success=True,
            message_id=simulated_id,
        )

    def clear(self) -> None:
        """Clear recorded messages (useful between test cases)."""
        self.sent_messages.clear()
