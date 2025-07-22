import os
import sys
from loguru import logger


def setup_logging():
    logger.remove()
    console_format = (
        "<green>{time:YYYY-MM-DD HH:mm:ss}</green> | "
        "<level>{level: <8}</level> | "
        "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - "
        "<level>{message}</level>"
    )
    logger.add(
        sys.stdout,
        format=console_format,
        level=os.getenv("LOG_LEVEL", "INFO"),
        colorize=True
    )

    log_file = os.getenv("LOG_FILE", "./logs/etl.log")
    os.makedirs(os.path.dirname(log_file), exist_ok=True)

    file_format = (
        "{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | "
        "{name}:{function}:{line} - {message}"
    )
    logger.add(
        log_file,
        format=file_format,
        level=os.getenv("LOG_LEVEL", "INFO"),
        rotation="100 MB",
        retention="7 days",
        compression="zip"
    )

    return logger
