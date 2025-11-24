"""
Centralized logging configuration for the RRI Orchestrator.

This module sets up a structured logging system that provides clear,
informative logs for debugging and monitoring.
"""

import logging
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional

from src.config import settings


def setup_logger(
    name: str = "rri_orchestrator",
    level: Optional[str] = None,
    log_file: Optional[str] = None,
) -> logging.Logger:
    """
    Configure and return a logger instance.
    
    Args:
        name: Logger name, typically the module name
        level: Log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_file: Optional file path to write logs
    
    Returns:
        Configured logger instance
    """
    logger = logging.getLogger(name)
    
    # Set log level based on environment
    if level is None:
        level = "DEBUG" if settings.is_development else "INFO"
    
    logger.setLevel(level)
    
    # Clear existing handlers to avoid duplicates
    logger.handlers.clear()
    
    # Console handler with custom formatting
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(level)
    
    # Format: [2024-01-15 10:30:45] INFO - module_name - Message
    console_format = logging.Formatter(
        fmt="[%(asctime)s] %(levelname)s - %(name)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )
    console_handler.setFormatter(console_format)
    logger.addHandler(console_handler)
    
    # File handler if log file specified
    if log_file:
        log_path = Path(log_file)
        log_path.parent.mkdir(parents=True, exist_ok=True)
        
        file_handler = logging.FileHandler(log_path)
        file_handler.setLevel(level)
        
        # More detailed format for file logs
        file_format = logging.Formatter(
            fmt="[%(asctime)s] %(levelname)s - %(name)s - %(funcName)s:%(lineno)d - %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S"
        )
        file_handler.setFormatter(file_format)
        logger.addHandler(file_handler)
    
    return logger


def get_logger(name: str) -> logging.Logger:
    """
    Get a logger instance for a specific module.
    
    This is the primary function to use when you need a logger in your code.
    
    Args:
        name: Module name, typically __name__
    
    Returns:
        Logger instance configured for the application
    """
    return logging.getLogger(f"rri_orchestrator.{name}")


# Application-wide logger instance
logger = setup_logger()
