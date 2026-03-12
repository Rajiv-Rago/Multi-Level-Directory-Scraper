"""Structured logging configuration with dual output (console + JSON file)."""

from __future__ import annotations

import logging
import logging.config
from pathlib import Path

import structlog


def setup_logging(log_level: str, log_file: Path | None = None) -> structlog.stdlib.BoundLogger:
    """Configure structlog with console (pretty) and optional JSON file output."""
    level = getattr(logging, log_level.upper(), logging.INFO)

    shared_processors: list = [
        structlog.contextvars.merge_contextvars,
        structlog.stdlib.filter_by_level,
        structlog.stdlib.add_log_level,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.processors.UnicodeDecoder(),
        structlog.stdlib.ProcessorFormatter.wrap_for_formatter,
    ]

    handlers: dict = {
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "console",
            "level": log_level.upper(),
        },
    }

    formatters: dict = {
        "console": {
            "()": structlog.stdlib.ProcessorFormatter,
            "processor": structlog.dev.ConsoleRenderer(colors=True),
        },
    }

    handler_names = ["console"]

    if log_file is not None:
        log_file.parent.mkdir(parents=True, exist_ok=True)
        handlers["file"] = {
            "class": "logging.FileHandler",
            "filename": str(log_file),
            "formatter": "json",
            "level": log_level.upper(),
        }
        formatters["json"] = {
            "()": structlog.stdlib.ProcessorFormatter,
            "processor": structlog.processors.JSONRenderer(),
        }
        handler_names.append("file")

    logging.config.dictConfig(
        {
            "version": 1,
            "disable_existing_loggers": False,
            "handlers": handlers,
            "formatters": formatters,
            "root": {
                "handlers": handler_names,
                "level": level,
            },
        }
    )

    structlog.configure(
        processors=shared_processors,
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=False,
    )

    return structlog.get_logger()
