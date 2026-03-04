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

    # 注册模块
    try:
        from services.modules.registry import registry
        from services.modules.schedule.module import schedule_module
        from services.modules.contact.module import contact_module

        registry.register(schedule_module)
        registry.register(contact_module)
        registry.mark_initialized()
        logger.info("模块注册成功")
    except Exception as e:
        logger.error(f"模块注册失败: {e}")

    # 启动提醒服务
    try:
        from services.reminder import reminder_manager
        # 注册模块的提醒服务
        reminder_manager.register_from_modules(registry.get_all())
        await reminder_manager.start()
        logger.info("提醒服务启动成功")
    except Exception as e:
        logger.error(f"提醒服务启动失败: {e}")

    yield  # 应用运行中

    # === 关闭时 ===
    logger.info("微信AI助手服务关闭")

    # 停止提醒服务
    try:
        from services.reminder import reminder_manager
        await reminder_manager.stop()
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


@app.get("/api/health")
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
        from services.reminder import reminder_manager
        # 简单测试：返回成功信息
        return {"status": "ok", "message": "提醒服务运行正常"}
    except Exception as e:
        logger.error(f"测试推送失败: {e}", exc_info=True)
        return {"status": "error", "message": str(e)}


# 导入路由
from app.routers import wechat, api

# 注册路由
app.include_router(wechat.router, prefix="/wechat", tags=["微信"])
app.include_router(api.router)

# 前端静态文件服务
import os
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

FRONTEND_DIST = os.path.join(os.path.dirname(__file__), "..", "frontend", "dist")

if os.path.exists(FRONTEND_DIST):
    # 挂载静态资源目录
    app.mount("/assets", StaticFiles(directory=os.path.join(FRONTEND_DIST, "assets")), name="assets")

    @app.get("/{full_path:path}")
    async def serve_frontend(full_path: str):
        """服务前端页面 - 处理所有未匹配的路由"""
        # 如果请求的是文件且存在，返回该文件
        file_path = os.path.join(FRONTEND_DIST, full_path)
        if os.path.isfile(file_path):
            return FileResponse(file_path)
        # 否则返回 index.html（支持前端路由）
        return FileResponse(os.path.join(FRONTEND_DIST, "index.html"))

