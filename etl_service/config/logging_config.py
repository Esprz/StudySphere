import os
import sys
from loguru import logger


def setup_logging():
    logger.remove()

    is_test_mode = os.getenv("TEST_MODE", "false").lower() == "true"
    is_development = os.getenv("ENVIRONMENT", "production").lower() in ["development", "dev"]

    console_format = (
        "<green>{time:YYYY-MM-DD HH:mm:ss}</green> | "
        "<level>{level: <8}</level> | "
        "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - "
        "<level>{message}</level>"
    )
    
    file_format = (
        "{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | "
        "{name}:{function}:{line} - {message}"
    )
    
    if is_test_mode or is_development:
        # Test/Development Mode: Console + File
        logger.add(
            sys.stdout,
            format=console_format,
            level=os.getenv("LOG_LEVEL", "DEBUG"),
            colorize=True,
        )
        
        log_file = os.getenv("LOG_FILE", "./logs/etl.log")
        os.makedirs(os.path.dirname(log_file), exist_ok=True)
        logger.add(
            log_file,
            format=file_format,
            level=os.getenv("LOG_LEVEL", "DEBUG"),
            rotation="100 MB",
            retention="7 days",
            compression="zip",
        )
        
    else:
        # Production Mode: File Only
        log_file = os.getenv("LOG_FILE", "./logs/etl.log")
        os.makedirs(os.path.dirname(log_file), exist_ok=True)
        logger.add(
            log_file,
            format=file_format,
            level=os.getenv("LOG_LEVEL", "INFO"),
            rotation="100 MB",
            retention="30 days",
            compression="zip",
        )
    
    return logger