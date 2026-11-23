"""Factory for instantiating the configured email delivery service."""

import os
from typing import Optional

from app.core.config import settings
from app.services.email.base import EmailServiceBase
from app.services.email.console import ConsoleEmailService
from app.services.email.smtp import SmtpEmailService

_service_instance: Optional[EmailServiceBase] = None
_console_singleton = ConsoleEmailService()


def get_email_service(override_backend: Optional[str] = None) -> EmailServiceBase:
    """Return configured email service instance based on environment settings.

    In test environments (or under pytest), default routes to ConsoleEmailService
    to guarantee zero external socket connections or test email leakage.
    """
    if override_backend:
        backend = override_backend
    elif os.getenv("PYTEST_CURRENT_TEST") or settings.is_test() or settings.ENVIRONMENT == "test":
        return _console_singleton
    else:
        backend = settings.EMAIL_BACKEND

    if backend == "smtp":
        return SmtpEmailService()
    elif backend in ("console", "test"):
        return _console_singleton
    else:
        return _console_singleton
