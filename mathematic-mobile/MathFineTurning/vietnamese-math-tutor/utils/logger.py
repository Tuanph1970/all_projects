"""
Logging configuration for Vietnamese Grade 12 Math Tutor.

Provides colored console output and file logging.
"""

import logging
import sys
from pathlib import Path
from datetime import datetime
from typing import Optional

try:
    import colorlog
    HAS_COLORLOG = True
except ImportError:
    HAS_COLORLOG = False


# Logger cache
_loggers = {}


def setup_logger(
    name: str = "math_tutor",
    level: int = logging.INFO,
    log_file: Optional[Path] = None,
    console: bool = True,
) -> logging.Logger:
    """
    Set up a logger with colored console output and optional file logging.

    Args:
        name: Logger name
        level: Logging level (default: INFO)
        log_file: Optional path to log file
        console: Whether to log to console (default: True)

    Returns:
        Configured logger instance
    """
    # Return cached logger if exists
    if name in _loggers:
        return _loggers[name]

    logger = logging.getLogger(name)
    logger.setLevel(level)
    logger.handlers = []  # Clear existing handlers

    # Log format
    log_format = "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s"
    date_format = "%Y-%m-%d %H:%M:%S"

    # Console handler with colors
    if console:
        if HAS_COLORLOG:
            console_format = (
                "%(log_color)s%(asctime)s | %(levelname)-8s%(reset)s | "
                "%(cyan)s%(name)s%(reset)s | %(message)s"
            )
            console_handler = colorlog.StreamHandler(sys.stdout)
            console_handler.setFormatter(colorlog.ColoredFormatter(
                console_format,
                datefmt=date_format,
                log_colors={
                    'DEBUG': 'white',
                    'INFO': 'green',
                    'WARNING': 'yellow',
                    'ERROR': 'red',
                    'CRITICAL': 'red,bg_white',
                }
            ))
        else:
            console_handler = logging.StreamHandler(sys.stdout)
            console_handler.setFormatter(logging.Formatter(log_format, date_format))

        console_handler.setLevel(level)
        logger.addHandler(console_handler)

    # File handler
    if log_file:
        log_file = Path(log_file)
        log_file.parent.mkdir(parents=True, exist_ok=True)

        file_handler = logging.FileHandler(log_file, encoding='utf-8')
        file_handler.setFormatter(logging.Formatter(log_format, date_format))
        file_handler.setLevel(level)
        logger.addHandler(file_handler)

    # Cache logger
    _loggers[name] = logger

    return logger


def get_logger(name: str = "math_tutor") -> logging.Logger:
    """
    Get or create a logger by name.

    Args:
        name: Logger name

    Returns:
        Logger instance
    """
    if name not in _loggers:
        return setup_logger(name)
    return _loggers[name]


def setup_training_logger(output_dir: Path) -> logging.Logger:
    """
    Set up logger for training with file output.

    Args:
        output_dir: Directory for log files

    Returns:
        Configured training logger
    """
    log_file = output_dir / "logs" / f"training_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
    return setup_logger(
        name="training",
        level=logging.INFO,
        log_file=log_file,
        console=True
    )


def setup_agent_logger(output_dir: Path) -> logging.Logger:
    """
    Set up logger for agent operations.

    Args:
        output_dir: Directory for log files

    Returns:
        Configured agent logger
    """
    log_file = output_dir / "logs" / f"agent_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
    return setup_logger(
        name="agent",
        level=logging.DEBUG,  # More verbose for debugging agent
        log_file=log_file,
        console=True
    )


class LoggerMixin:
    """
    Mixin class to add logging capability to any class.

    Usage:
        class MyClass(LoggerMixin):
            def my_method(self):
                self.logger.info("Doing something...")
    """

    @property
    def logger(self) -> logging.Logger:
        if not hasattr(self, '_logger'):
            self._logger = get_logger(self.__class__.__name__)
        return self._logger


if __name__ == "__main__":
    # Test logging
    logger = setup_logger("test", level=logging.DEBUG)
    logger.debug("This is a debug message")
    logger.info("This is an info message")
    logger.warning("This is a warning message")
    logger.error("This is an error message")
    logger.critical("This is a critical message")
