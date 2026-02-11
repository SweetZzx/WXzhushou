"""
日志工具
"""
import logging
import sys
from pathlib import Path
from loguru import logger

from config import LOG_LEVEL, LOG_FILE


def setup_logger():
    """配置日志系统"""

    # 确保日志目录存在
    log_path = Path(LOG_FILE)
    log_path.parent.mkdir(parents=True, exist_ok=True)

    # 配置loguru
    logger.remove()  # 移除默认处理器

    # 控制台输出
    logger.add(
        sys.stdout,
        format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>",
        level=LOG_LEVEL,
        colorize=True
    )

    # 文件输出
    logger.add(
        log_path,
        format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} - {message}",
        level=LOG_LEVEL,
        rotation="10 MB",  # 文件大小超过10MB时轮转
        retention="30 days",  # 保留30天
        compression="zip",  # 压缩旧日志
        encoding="utf-8"
    )

    return logger


# 创建全局日志实例
log = setup_logger()


def get_logger(name: str = None):
    """
    获取日志记录器

    Args:
        name: 日志记录器名称

    Returns:
        日志记录器实例
    """
    if name:
        return logger.bind(name=name)
    return logger
