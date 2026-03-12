"""
Logging configuration for the Mathematics LLM OCR Service.
"""
import json
import sys
from datetime import timezone
from loguru import logger


# Fields that are emitted as top-level keys in the JSON envelope.
# All other extra fields are merged in under "context".
_ENVELOPE_FIELDS = frozenset({"service_name", "service_version", "environment"})


def _make_json_sink(level: str):
    """
    Return a loguru sink function that writes structured JSON to stdout.

    Every call-site extra is serialised into the "context" object so fields
    like request_id, model_name, and user_id appear automatically in every
    log line without requiring format-string changes.
    """
    import sys as _sys

    def _sink(message):
        record = message.record
        extra = record["extra"]

        context = {
            k: v for k, v in extra.items()
            if k not in _ENVELOPE_FIELDS
        }

        entry = {
            "time": record["time"].astimezone(timezone.utc).strftime(
                "%Y-%m-%dT%H:%M:%S.%f"
            )[:-3] + "Z",
            "level": record["level"].name,
            "service": extra.get("service_name", ""),
            "version": extra.get("service_version", ""),
            "environment": extra.get("environment", ""),
            "logger": record["name"],
            "function": record["function"],
            "line": record["line"],
            "message": record["message"],
        }

        if context:
            entry["context"] = context

        if record["exception"] is not None:
            exc_type, exc_value, _ = record["exception"]
            entry["exception"] = {
                "type": exc_type.__name__ if exc_type else None,
                "value": str(exc_value) if exc_value else None,
            }

        _sys.stdout.write(json.dumps(entry, default=str) + "\n")
        _sys.stdout.flush()

    return _sink


def setup_logging(logging_settings) -> None:
    """
    Configure loguru based on application logging settings.

    Args:
        logging_settings: LoggingSettings instance from config.settings
    """
    # Remove the default loguru handler
    logger.remove()

    # Bind shared context fields so they are available on every record
    logger.configure(
        extra={
            "service_name": logging_settings.service_name,
            "service_version": logging_settings.service_version,
            "environment": logging_settings.environment,
        }
    )

    if logging_settings.format == "json":
        # Structured JSON sink: includes all extra context automatically
        logger.add(
            _make_json_sink(logging_settings.level),
            level=logging_settings.level,
            format="{message}",   # raw — the sink handles serialisation
            colorize=False,
            backtrace=False,
            diagnose=False,
        )
    else:
        text_format = (
            "{time:YYYY-MM-DD HH:mm:ss.SSS} | {level: <8} | "
            "{name}:{function}:{line} | {message}"
        )
        logger.add(
            sys.stdout,
            format=text_format,
            level=logging_settings.level,
            colorize=True,
            backtrace=True,
            diagnose=True,
        )

    # File handler (optional) — always uses JSON for structured storage
    if logging_settings.file_path:
        logger.add(
            _make_json_sink(logging_settings.level),
            level=logging_settings.level,
            format="{message}",
            rotation=logging_settings.max_file_size,
            retention=logging_settings.backup_count,
            compression="zip",
            backtrace=False,
            diagnose=False,
        )

    logger.info(
        "Logging initialised",
        level=logging_settings.level,
        format=logging_settings.format,
        environment=logging_settings.environment,
    )
