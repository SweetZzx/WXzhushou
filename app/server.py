"""
FastAPI 服务器配置
使用 lifespan 管理应用生命周期
"""
from contextlib import asynccontextmanager
from fastapi import FastAPI
import logging

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(_app: FastAPI):
    """应用生命周期管理"""
    # === 启动时 ===
    logger.info("微信AI助手服务启动中...")

    # 初始化数据库
    try:
        from database.session import init_db
        await init_db()
        logger.info("数据库初始化成功")
    except Exception as e:
        logger.error(f"数据库初始化失败: {e}")

    # 启动提醒服务
    try:
        from services.reminder_service import reminder_service
        await reminder_service.start()
        logger.info("提醒服务启动成功")
    except Exception as e:
        logger.error(f"提醒服务启动失败: {e}")

    yield  # 应用运行中

    # === 关闭时 ===
    logger.info("微信AI助手服务关闭")

    # 停止提醒服务
    try:
        from services.reminder_service import reminder_service
        await reminder_service.stop()
        logger.info("提醒服务已停止")
    except Exception as e:
        logger.error(f"停止提醒服务失败: {e}")

    # 关闭数据库连接
    try:
        from database.session import close_db
        await close_db()
        logger.info("数据库连接已关闭")
    except Exception as e:
        logger.error(f"关闭数据库连接失败: {e}")


# 创建 FastAPI 应用
app = FastAPI(
    title="微信AI助手",
    description="基于智谱GLM的微信机器人服务 - 支持日程管理",
    version="2.0.0",
    lifespan=lifespan
)


@app.get("/")
async def root():
    """根路径"""
    return {
        "message": "微信AI助手服务运行中",
        "status": "ok",
        "version": "2.0.0",
        "features": ["AI对话", "日程管理"]
    }


@app.get("/health")
async def health_check():
    """健康检查接口"""
    return {
        "status": "healthy",
        "service": "wechat-ai-assistant",
        "version": "2.0.0"
    }


@app.post("/test/push")
async def test_push():
    """测试推送接口 - 手动触发测试提醒"""
    try:
        from services.reminder_service import reminder_service
        await reminder_service.send_test_reminder_now()
        return {"status": "ok", "message": "测试提醒已发送，请查看日志"}
    except Exception as e:
        logger.error(f"测试推送失败: {e}", exc_info=True)
        return {"status": "error", "message": str(e)}


# 导入路由
from app.routers import wechat

# 注册路由
app.include_router(wechat.router, prefix="/wechat", tags=["微信"])
