"""Standardized logging configuration for Converge AI."""

import logging
import sys
from app.core.config import Settings


def setup_logging(settings: Settings) -> logging.Logger:
    """Configure application logging with safe formatting and log levels."""
    log_format = (
        "[%(asctime)s] [%(process)d] [%(levelname)s] "
        "[%(name)s] %(message)s"
    )
    date_format = "%Y-%m-%d %H:%M:%S"

    level = getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO)

    # Configure root logger
    logging.basicConfig(
        level=level,
        format=log_format,
        datefmt=date_format,
        stream=sys.stdout,
        force=True,
    )

    # Silence overly verbose external loggers
    logging.getLogger("uvicorn.access").setLevel(level)
    logging.getLogger("uvicorn.error").setLevel(level)

    logger = logging.getLogger("converge_ai")
    logger.setLevel(level)
    return logger
