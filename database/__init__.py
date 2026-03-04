"""
数据库模块
"""
from .base import Base
from .session import init_db, get_db, AsyncSessionLocal

# 别名，兼容旧代码
db_session = type('db_session', (), {'AsyncSessionLocal': AsyncSessionLocal})()

__all__ = ["Base", "init_db", "get_db", "AsyncSessionLocal", "db_session"]
