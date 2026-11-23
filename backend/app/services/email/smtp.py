"""Asynchronous SMTP email delivery service with TLS support."""

import asyncio
import logging
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.utils import formataddr, make_msgid
from typing import Optional

from app.core.config import settings
from app.services.email.base import EmailDispatchResult, EmailMessage, EmailServiceBase

logger = logging.getLogger(__name__)


class SmtpEmailService(EmailServiceBase):
    """Production SMTP email service delivering via standard SMTP/STARTTLS relays."""

    def __init__(
        self,
        host: Optional[str] = None,
        port: Optional[int] = None,
        use_tls: Optional[bool] = None,
        username: Optional[str] = None,
        password: Optional[str] = None,
        default_sender_email: Optional[str] = None,
        default_sender_name: Optional[str] = None,
    ) -> None:
        self.host = host or settings.SMTP_HOST or "smtp.gmail.com"
        self.port = port or settings.SMTP_PORT or 587
        self.use_tls = use_tls if use_tls is not None else settings.SMTP_USE_TLS
        self.username = username or settings.SMTP_USERNAME or settings.EMAIL_SENDER_ADDRESS
        self.password = password or settings.SMTP_PASSWORD
        self.default_sender_email = default_sender_email or settings.EMAIL_SENDER_ADDRESS
        self.default_sender_name = default_sender_name or settings.EMAIL_SENDER_NAME

    def _sync_send(self, msg: MIMEMultipart, recipients: list[str]) -> str:
        """Blocking synchronous SMTP transmission executed in background thread."""
        logger.info(
            "Connecting to SMTP relay at %s:%d for %d recipients",
            self.host,
            self.port,
            len(recipients),
        )

        with smtplib.SMTP(self.host, self.port, timeout=15) as server:
            if self.use_tls:
                server.starttls()

            if self.username and self.password:
                # Support both spaced and stripped passwords
                clean_pwd = self.password.strip()
                try:
                    server.login(self.username, clean_pwd)
                except smtplib.SMTPAuthenticationError:
                    # Retry with spaces removed if user provided 4-block format
                    stripped = clean_pwd.replace(" ", "")
                    server.login(self.username, stripped)

            server.send_message(msg, from_addr=msg["From"], to_addrs=recipients)

        return msg["Message-ID"]

    async def send_email(self, message: EmailMessage) -> EmailDispatchResult:
        """Send MIME multipart email asynchronously in a dedicated worker thread."""
        if not message.to:
            return EmailDispatchResult(success=False, error="Recipient list cannot be empty")

        sender_email = message.sender_address or self.default_sender_email
        sender_name = message.sender_name or self.default_sender_name

        # Build MIME structure
        msg = MIMEMultipart("alternative")
        msg["Subject"] = message.subject
        msg["From"] = formataddr((sender_name, sender_email))
        msg["To"] = ", ".join(message.to)
        msg["Message-ID"] = make_msgid(domain=sender_email.split("@")[-1] if "@" in sender_email else None)

        if message.reply_to:
            msg["Reply-To"] = message.reply_to

        if message.cc:
            msg["Cc"] = ", ".join(message.cc)

        # Attach text and HTML alternatives
        text_body = message.text_body or "Please view this message in an HTML-capable email client."
        msg.attach(MIMEText(text_body, "plain", "utf-8"))
        msg.attach(MIMEText(message.html_body, "html", "utf-8"))

        all_recipients = list(message.to)
        if message.cc:
            all_recipients.extend(message.cc)
        if message.bcc:
            all_recipients.extend(message.bcc)

        try:
            # Delegate blocking I/O to asyncio thread pool
            msg_id = await asyncio.to_thread(self._sync_send, msg, all_recipients)
            logger.info("Successfully delivered email '%s' [ID: %s]", message.subject, msg_id)
            return EmailDispatchResult(success=True, message_id=msg_id)
        except Exception as e:
            logger.error("Failed to deliver email '%s': %s", message.subject, e, exc_info=True)
            return EmailDispatchResult(success=False, error=str(e))
