"""Email delivery and notification services."""

from app.services.email.base import EmailDispatchResult, EmailMessage, EmailServiceBase
from app.services.email.console import ConsoleEmailService
from app.services.email.factory import get_email_service
from app.services.email.smtp import SmtpEmailService
from app.services.email.template import render_commercial_quote_email

__all__ = [
    "EmailMessage",
    "EmailDispatchResult",
    "EmailServiceBase",
    "SmtpEmailService",
    "ConsoleEmailService",
    "get_email_service",
    "render_commercial_quote_email",
]
