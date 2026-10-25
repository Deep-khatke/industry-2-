"""Structured JSON logging with privacy-preserving data redaction."""

import json
import logging
import re
import sys
from datetime import UTC, datetime
from typing import Any

SENSITIVE_KEY_PATTERNS = [
    re.compile(r"password", re.IGNORECASE),
    re.compile(r"secret", re.IGNORECASE),
    re.compile(r"token", re.IGNORECASE),
    re.compile(r"api[_-]?key", re.IGNORECASE),
    re.compile(r"private[_-]?key", re.IGNORECASE),
]

IPV4_OCTET_PATTERN = re.compile(r"(\b\d{1,3}\.\d{1,3}\.)\d{1,3}\.\d{1,3}\b")


def sanitize_sensitive_data(val: Any) -> Any:
    """Recursively redact secrets and mask full subscriber IP addresses."""
    if isinstance(val, dict):
        sanitized = {}
        for k, v in val.items():
            if any(p.search(str(k)) for p in SENSITIVE_KEY_PATTERNS):
                sanitized[k] = "[REDACTED]"
            else:
                sanitized[k] = sanitize_sensitive_data(v)
        return sanitized
    if isinstance(val, list):
        return [sanitize_sensitive_data(item) for item in val]
    if isinstance(val, str):
        # Mask subscriber host portion of IP addresses (retain /16 or /24 prefix)
        return IPV4_OCTET_PATTERN.sub(r"\g<1>xxx.xxx", val)
    return val


class JsonFormatter(logging.Formatter):
    """Custom logging formatter that outputs one JSON object per line."""

    def format(self, record: logging.LogRecord) -> str:
        log_entry: dict[str, Any] = {
            "timestamp": datetime.now(UTC).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }

        # Attach custom extra fields if present
        for key, val in record.__dict__.items():
            if key not in (
                "args",
                "asctime",
                "created",
                "exc_info",
                "exc_text",
                "filename",
                "funcName",
                "levelname",
                "levelno",
                "lineno",
                "module",
                "msecs",
                "msg",
                "name",
                "pathname",
                "process",
                "processName",
                "relativeCreated",
                "stack_info",
                "thread",
                "threadName",
            ):
                log_entry[key] = sanitize_sensitive_data(val)

        if record.exc_info:
            log_entry["exception"] = self.formatException(record.exc_info)

        return json.dumps(log_entry)


class StructuredLogger:
    """Convenience wrapper providing contextual structured logging."""

    def __init__(self, name: str) -> None:
        self._logger = logging.getLogger(name)
        if not self._logger.handlers:
            handler = logging.StreamHandler(sys.stdout)
            handler.setFormatter(JsonFormatter())
            self._logger.addHandler(handler)
            self._logger.setLevel(logging.INFO)
            self._logger.propagate = False

    def info(self, msg: str, **kwargs: Any) -> None:
        self._logger.info(msg, extra=kwargs)

    def warning(self, msg: str, **kwargs: Any) -> None:
        self._logger.warning(msg, extra=kwargs)

    def error(self, msg: str, **kwargs: Any) -> None:
        self._logger.error(msg, extra=kwargs)

    def debug(self, msg: str, **kwargs: Any) -> None:
        self._logger.debug(msg, extra=kwargs)


def get_logger(name: str) -> StructuredLogger:
    """Get or create a StructuredLogger instance."""
    return StructuredLogger(name)
