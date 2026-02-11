"""
数据库会话管理
"""
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from config import DATABASE_URL
import logging

logger = logging.getLogger(__name__)

# 创建异步引擎
engine = None
AsyncSessionLocal = None

async def init_db():
    """初始化数据库"""
    global engine, AsyncSessionLocal

    if engine is not None:
        return

    # 创建异步引擎
    engine = create_async_engine(
        DATABASE_URL,
        echo=False,  # 设置为 True 可以看到 SQL 语句
        pool_pre_ping=True,
        pool_recycle=3600,
    )

    # 创建会话工厂
    AsyncSessionLocal = async_sessionmaker(
        engine,
        class_=AsyncSession,
        expire_on_commit=False,
        autocommit=False,
        autoflush=False,
    )

    logger.info(f"数据库已连接: {DATABASE_URL}")

    # 导入所有模型，确保表被注册
    from models.schedule import Schedule
    from database.base import Base

    # 创建所有表
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    logger.info("数据库表创建完成")


async def get_db() -> AsyncSession:
    """获取数据库会话"""
    if AsyncSessionLocal is None:
        await init_db()

    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


async def close_db():
    """关闭数据库连接"""
    global engine

    if engine is not None:
        await engine.dispose()
        engine = None
        logger.info("数据库连接已关闭")
