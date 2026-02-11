"""
FastAPI 服务器配置
"""
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
import logging

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# 创建FastAPI应用
app = FastAPI(
    title="微信AI助手",
    description="基于智谱GLM的微信机器人服务",
    version="1.0.0"
)


@app.on_event("startup")
async def startup_event():
    """应用启动时的事件"""
    logger.info("微信AI助手服务启动中...")


@app.on_event("shutdown")
async def shutdown_event():
    """应用关闭时的事件"""
    logger.info("微信AI助手服务关闭")


@app.get("/")
async def root():
    """根路径"""
    return {
        "message": "微信AI助手服务运行中",
        "status": "ok",
        "version": "1.0.0"
    }


@app.get("/health")
async def health_check():
    """健康检查接口"""
    return {
        "status": "healthy",
        "service": "wechat-ai-assistant"
    }


# 导入路由
from app.routers import wechat

# 注册路由
app.include_router(wechat.router, prefix="/wechat", tags=["微信"])
