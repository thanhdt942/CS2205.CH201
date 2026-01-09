# src/logger.py
import sys
from loguru import logger

logger.remove()

logger.add(
    sys.stderr,
    format="<green>{time:HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>",
    level="INFO"
)

logger.add("logs/app_{time:YYYY-MM-DD}.log", rotation="1 day", level="DEBUG")

__all__ = ["logger"]