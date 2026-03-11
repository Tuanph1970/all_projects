"""
Logging configuration for the Mathematics LLM OCR Service.
"""
import sys
from loguru import logger


def setup_logging(logging_settings) -> None:
    """
    Configure loguru based on application logging settings.

    Args:
        logging_settings: LoggingSettings instance from config.settings
    """
    # Remove the default loguru handler
    logger.remove()

    log_format = (
        "{time:YYYY-MM-DD HH:mm:ss.SSS} | {level: <8} | "
        "{name}:{function}:{line} | {message}"
    )

    if logging_settings.format == "json":
        log_format = (
            '{{"time":"{time:YYYY-MM-DD HH:mm:ss.SSS}",'
            '"level":"{level}",'
            '"service":"{extra[service_name]}",'
            '"version":"{extra[service_version]}",'
            '"environment":"{extra[environment]}",'
            '"logger":"{name}",'
            '"function":"{function}",'
            '"line":{line},'
            '"message":"{message}"}}'
        )

    # Console handler
    logger.add(
        sys.stdout,
        format=log_format,
        level=logging_settings.level,
        colorize=logging_settings.format != "json",
        backtrace=True,
        diagnose=True,
    )

    # File handler (optional)
    if logging_settings.file_path:
        logger.add(
            logging_settings.file_path,
            format=log_format,
            level=logging_settings.level,
            rotation=logging_settings.max_file_size,
            retention=logging_settings.backup_count,
            compression="zip",
            backtrace=True,
            diagnose=False,  # Avoid sensitive data in file logs
        )

    # Bind shared context fields to every log record
    logger.configure(
        extra={
            "service_name": logging_settings.service_name,
            "service_version": logging_settings.service_version,
            "environment": logging_settings.environment,
        }
    )

    logger.info(
        f"Logging initialised | level={logging_settings.level} "
        f"format={logging_settings.format} "
        f"environment={logging_settings.environment}"
    )
