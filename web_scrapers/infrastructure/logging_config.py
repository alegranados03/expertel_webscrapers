"""
Logging configuration for the web scrapers application
"""

import logging
import sys
from typing import Optional


def setup_logging(log_level: str = "INFO", log_file: Optional[str] = None) -> logging.Logger:
    """
    Setup logging configuration for the application.

    Configures the ROOT logger so all loggers (including scraper class names
    like ATTPDFInvoiceScraperStrategy) inherit the configuration.

    Args:
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_file: Optional log file path. If None, logs only to console.

    Returns:
        Configured logger instance
    """
    level = getattr(logging, log_level.upper())

    # Create formatter
    formatter = logging.Formatter(
        fmt="%(asctime)s - %(name)s - %(levelname)s - %(message)s", datefmt="%Y-%m-%d %H:%M:%S"
    )

    # Configure ROOT logger so ALL loggers inherit this configuration
    root_logger = logging.getLogger()
    root_logger.setLevel(level)
    root_logger.handlers.clear()

    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(level)
    console_handler.setFormatter(formatter)
    root_logger.addHandler(console_handler)

    # File handler (if specified)
    if log_file:
        file_handler = logging.FileHandler(log_file)
        file_handler.setLevel(level)
        file_handler.setFormatter(formatter)
        root_logger.addHandler(file_handler)

    # Return web_scrapers logger for backward compatibility
    return logging.getLogger("web_scrapers")


def get_logger(name: str = "web_scrapers") -> logging.Logger:
    """
    Get logger instance.

    Args:
        name: Logger name

    Returns:
        Logger instance
    """
    base = "web_scrapers"
    full_name = base if name in (None, "", base) else f"{base}.{name}"
    return logging.getLogger(full_name)
