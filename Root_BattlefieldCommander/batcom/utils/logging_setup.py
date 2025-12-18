"""
Logging configuration for BATCOM

Sets up Python logging with rotating file handlers and proper formatting.
"""

import logging
import logging.handlers
import os
from pathlib import Path
from datetime import datetime


def setup_logging(config=None):
    """
    Configure logging for BATCOM

    Args:
        config: Dictionary with logging configuration
                - level: Logging level (DEBUG, INFO, WARNING, ERROR)
                - arma_console: Whether to also log to Arma console (not implemented yet)

    Returns:
        Logger instance
    """
    if config is None:
        config = {}

    # Parse log level
    level_str = config.get('level', 'INFO').upper()
    level = getattr(logging, level_str, logging.INFO)

    # Create logger
    logger = logging.getLogger('batcom')
    logger.setLevel(level)

    # Clear existing handlers
    logger.handlers.clear()

    # Create logs directory if it doesn't exist
    # Use forward slashes for cross-platform compatibility
    try:
        log_dir = Path.cwd() / '@BATCOM' / 'logs'
        log_dir.mkdir(parents=True, exist_ok=True)
    except (OSError, PermissionError) as e:
        # Fallback to a simpler path if @BATCOM fails (Linux compatibility)
        print(f"[BATCOM] Warning: Failed to create {log_dir}: {e}")
        try:
            log_dir = Path.cwd() / 'batcom_logs'
            log_dir.mkdir(parents=True, exist_ok=True)
            print(f"[BATCOM] Using fallback log directory: {log_dir}")
        except Exception as fallback_error:
            # Last resort: use temp directory
            import tempfile
            log_dir = Path(tempfile.gettempdir()) / 'batcom_logs'
            log_dir.mkdir(parents=True, exist_ok=True)
            print(f"[BATCOM] Using temp log directory: {log_dir}")

    # Create timestamped log filename (e.g., batcom_log_2025_12_02_16_25_30.log)
    timestamp = datetime.now().strftime('%Y_%m_%d_%H_%M_%S')
    log_file = log_dir / f'batcom_log_{timestamp}.log'

    # File handler (no rotation needed since each initialization creates a new file)
    try:
        file_handler = logging.FileHandler(
            log_file,
            encoding='utf-8'
        )
        file_handler.setLevel(level)

        # Formatter
        formatter = logging.Formatter(
            '[%(asctime)s] [%(levelname)s] [%(name)s] %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        file_handler.setFormatter(formatter)

        # Add handler
        logger.addHandler(file_handler)
    except (OSError, PermissionError) as e:
        # If file handler fails, fall back to stderr handler for Linux compatibility
        print(f"[BATCOM] Warning: Failed to create file handler at {log_file}: {e}")
        print(f"[BATCOM] Falling back to stderr logging")

        stderr_handler = logging.StreamHandler()
        stderr_handler.setLevel(level)
        formatter = logging.Formatter(
            '[%(asctime)s] [%(levelname)s] [%(name)s] %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        stderr_handler.setFormatter(formatter)
        logger.addHandler(stderr_handler)

    logger.info('Logging initialized at level %s', level_str)
    logger.info('Log file: %s', log_file)

    return logger


def get_logger(name='batcom'):
    """
    Get a logger instance

    Args:
        name: Logger name (default: 'batcom')

    Returns:
        Logger instance
    """
    return logging.getLogger(name)
