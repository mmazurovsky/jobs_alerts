"""
Logging configuration for the application.
"""
import logging
import sys
from pathlib import Path


def setup_logging(log_file: Path = None):
    """
    Set up logging configuration.
    
    Args:
        log_file: Optional path to log file. If not provided, logs only to console.
    """
    # Create formatters
    console_formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    file_formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

    # Create handlers
    handlers = []
    
    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(console_formatter)
    handlers.append(console_handler)
    
    # File handler (if log_file is provided)
    if log_file:
        log_file.parent.mkdir(parents=True, exist_ok=True)
        file_handler = logging.FileHandler(log_file)
        file_handler.setFormatter(file_formatter)
        handlers.append(file_handler)

    # Configure root logger
    logging.basicConfig(
        level=logging.INFO,
        handlers=handlers
    ) 