"""
Logging utilities for Agent.
This module provides a function to set up the logger for the Agent.
The logger is set up with a StreamHandler that logs to stdout. 
The log level can be set to any level from the logging module. 
The default log level is INFO. 
The log format is set to include the timestamp, logger name, log level, and log message."""

import logging
import sys
from typing import Optional

# Global logger registry
_loggers = {}

def setup_logging(level: int = logging.INFO, log_file: Optional[str] = None):
    """Set up the root logging configuration for the application."""
    # Create root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(level)
    
    # Clear any existing handlers to avoid duplicates
    if root_logger.handlers:
        root_logger.handlers.clear()
    
    # Create formatter
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    
    # Create console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(level)
    console_handler.setFormatter(formatter)
    root_logger.addHandler(console_handler)
    
    # Create file handler if log file is specified
    if log_file:
        file_handler = logging.FileHandler(log_file)
        file_handler.setLevel(level)
        file_handler.setFormatter(formatter)
        root_logger.addHandler(file_handler)
    
    # Suppress excessive logging from libraries
    logging.getLogger('aiohttp').setLevel(logging.WARNING)
    logging.getLogger('asyncio').setLevel(logging.WARNING)

def get_logger(name: str) -> logging.Logger:
    """
    Get a logger for the specified module name.
    Ensures only one logger instance is created per module.
    """
    if name not in _loggers:
        _loggers[name] = logging.getLogger(name)
    return _loggers[name]