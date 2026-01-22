"""
Logging utility module.
"""

import logging
import sys
from logging.config import dictConfig
from pathlib import Path

from src.config.settings import LOGGING_CONFIG

def setup_logger(name: str = "FileSystemAgent") -> logging.Logger:
    """Setup and return a configured logger."""
    # Configure logging
    dictConfig(LOGGING_CONFIG)
    
    # Get logger
    logger = logging.getLogger(name)
    
    # Windows encoding fix
    if sys.platform == "win32":
        sys.stdout.reconfigure(encoding='utf-8')
        sys.stderr.reconfigure(encoding='utf-8')
    
    return logger
