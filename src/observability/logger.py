"""
Structured JSON logging for application events.

This module handles APPLICATION-LEVEL logging (errors, warnings, info messages).
For LLM call tracing, use src.observability.tracer instead.

Why structured logging?
- JSON output is machine-readable (easy to parse, filter, aggregate)
- Consistent schema across all logs (timestamp, level, logger, message, context)
- Works with log aggregation tools (CloudWatch, Datadog, etc.)
- Human-readable with jq: `cat logs.jsonl | jq .`

Example log entry:
{
  "timestamp": "2026-04-23T10:30:00Z",
  "level": "INFO",
  "logger": "causeway.portfolio",
  "message": "Portfolio analyzed successfully",
  "portfolio_id": "PORTFOLIO_001",
  "duration_ms": 1234,
  "num_holdings": 15
}

Usage:
    logger = get_logger(__name__)
    logger.info("Portfolio loaded", portfolio_id="P001", num_stocks=10)
    logger.error("Parsing failed", portfolio_id="P002", error="Invalid JSON")
"""

import json
import logging
import sys
from datetime import datetime
from pathlib import Path


class StructuredLogger:
    """
    Structured JSON logger for application events.

    Why JSON logging?
    - Machine-readable: Easy to parse with tools like jq, grep, or log aggregators
    - Structured: Each log entry has consistent fields (timestamp, level, message, context)
    - Searchable: Filter by any field without regex

    Usage:
        logger = StructuredLogger("causeway")
        logger.info("Portfolio analyzed", portfolio_id="P001", duration_ms=1234)
    """

    def __init__(self, name: str, log_file: Path | None = None) -> None:
        """
        Args:
            name: Logger name (typically module or component name).
            log_file: Optional file path for logs. If None, logs to stdout only.
        """
        self.name = name
        self.log_file = log_file

        self.logger = logging.getLogger(name)
        self.logger.setLevel(logging.DEBUG)
        self.logger.handlers = []
        self.logger.propagate = False  # Prevent double-logging if root logger has handlers

        formatter = self._json_formatter()

        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setFormatter(formatter)
        self.logger.addHandler(console_handler)

        if log_file:
            log_file.parent.mkdir(parents=True, exist_ok=True)
            file_handler = logging.FileHandler(log_file)
            file_handler.setFormatter(formatter)
            self.logger.addHandler(file_handler)

    def info(self, message: str, **kwargs) -> None:
        """Log an INFO level event with structured context."""
        self._log("INFO", message, kwargs)

    def warning(self, message: str, **kwargs) -> None:
        """Log a WARNING level event with structured context."""
        self._log("WARNING", message, kwargs)

    def error(self, message: str, **kwargs) -> None:
        """Log an ERROR level event with structured context."""
        self._log("ERROR", message, kwargs)

    def debug(self, message: str, **kwargs) -> None:
        """Log a DEBUG level event with structured context."""
        self._log("DEBUG", message, kwargs)

    def _log(self, level: str, message: str, context: dict) -> None:
        """Formats a structured entry and emits it via the standard logging backend."""
        log_entry = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "level": level,
            "logger": self.name,
            "message": message,
            **context,
        }
        self.logger.log(getattr(logging, level), json.dumps(log_entry))

    @staticmethod
    def _json_formatter() -> logging.Formatter:
        """Pass-through formatter — the message is already a JSON string."""
        return logging.Formatter("%(message)s")


# Factory

def get_logger(name: str, log_file: Path | None = None) -> StructuredLogger:
    """
    Creates a StructuredLogger for the given component.

    Usage:
        from src.observability.logger import get_logger
        logger = get_logger(__name__)
        logger.info("Processing started", portfolio_id="P001")
    """
    return StructuredLogger(name, log_file)
