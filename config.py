"""
配置文件
读取环境变量并提供配置项
"""
import os
from typing import Optional
from pathlib import Path

# 项目根目录
BASE_DIR = Path(__file__).parent

# 微信配置
WECHAT_APP_ID: str = os.getenv("WECHAT_APP_ID", "")
WECHAT_APP_SECRET: str = os.getenv("WECHAT_APP_SECRET", "")
WECHAT_TOKEN: str = os.getenv("WECHAT_TOKEN", "your_token_here")
WECHAT_ENCODING_AES_KEY: str = os.getenv("WECHAT_ENCODING_AES_KEY", "")
WECHAT_MODE: str = os.getenv("WECHAT_MODE", "normal")  # normal: 明文模式, safe: 安全模式

# 智谱AI配置
ZHIPU_API_KEY: str = os.getenv("ZHIPU_API_KEY", "")
ZHIPU_API_URL: str = os.getenv("ZHIPU_API_URL", "https://open.bigmodel.cn/api/paas/v4/chat/completions")
ZHIPU_API_BASE: str = os.getenv("ZHIPU_API_BASE", "https://open.bigmodel.cn/api/paas/v4")
ZHIPU_MODEL: str = os.getenv("ZHIPU_MODEL", "glm-4")
ZHIPU_TEMPERATURE: float = float(os.getenv("ZHIPU_TEMPERATURE", "0.7"))
ZHIPU_MAX_TOKENS: int = int(os.getenv("ZHIPU_MAX_TOKENS", "2000"))
ZHIPU_TIMEOUT: int = int(os.getenv("ZHIPU_TIMEOUT", "30"))

# LangChain 配置
LANGCHAIN_MODEL: str = os.getenv("LANGCHAIN_MODEL", "glm-4")
LANGCHAIN_TEMPERATURE: float = float(os.getenv("LANGCHAIN_TEMPERATURE", "0.7"))
LANGCHAIN_MAX_TOKENS: int = int(os.getenv("LANGCHAIN_MAX_TOKENS", "2000"))

# 服务器配置
SERVER_HOST: str = os.getenv("SERVER_HOST", "0.0.0.0")
SERVER_PORT: int = int(os.getenv("SERVER_PORT", "8000"))
SERVER_RELOAD: bool = os.getenv("SERVER_RELOAD", "false").lower() == "true"

# 日志配置
LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")
LOG_FILE: str = os.getenv("LOG_FILE", str(BASE_DIR / "data" / "logs" / "app.log"))
LOG_FORMAT: str = os.getenv(
    "LOG_FORMAT",
    "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)

# 数据库配置
DATABASE_URL: str = os.getenv("DATABASE_URL", "sqlite+aiosqlite:///data/schedules.db")

# 数据目录
DATA_DIR: str = os.getenv("DATA_DIR", str(BASE_DIR / "data"))

# AI对话配置
DEFAULT_SYSTEM_PROMPT: str = os.getenv(
    "DEFAULT_SYSTEM_PROMPT",
    "你是一个友好、乐于助人的AI助手。请用简洁、准确的语言回答用户的问题。"
)

# 上下文配置
CONTEXT_MEMORY_SIZE: int = int(os.getenv("CONTEXT_MEMORY_SIZE", "10"))  # 保留最近N轮对话

# 消息超时配置（微信要求5秒内响应）
WECHAT_REPLY_TIMEOUT: int = int(os.getenv("WECHAT_REPLY_TIMEOUT", "4"))


class Config:
    """配置类"""

    @staticmethod
    def validate() -> bool:
        """验证必需的配置项"""
        if not WECHAT_APP_ID:
            print("警告: WECHAT_APP_ID 未设置")
        if not WECHAT_APP_SECRET:
            print("警告: WECHAT_APP_SECRET 未设置")
        if not ZHIPU_API_KEY:
            print("错误: ZHIPU_API_KEY 未设置")
            return False
        return True

    @staticmethod
    def print_config() -> None:
        """打印配置信息（隐藏敏感信息）"""
        print("=" * 50)
        print("微信AI助手配置")
        print("=" * 50)
        print(f"微信APP ID: {WECHAT_APP_ID[:8]}...{WECHAT_APP_ID[-4:] if WECHAT_APP_ID else '未设置'}")
        print(f"微信APP Secret: {'已设置' if WECHAT_APP_SECRET else '未设置'}")
        print(f"微信Token: {WECHAT_TOKEN}")
        print(f"智谱API Key: {ZHIPU_API_KEY[:16]}...{ZHIPU_API_KEY[-4:] if ZHIPU_API_KEY else '未设置'}")
        print(f"智谱模型: {ZHIPU_MODEL}")
        print(f"服务器地址: {SERVER_HOST}:{SERVER_PORT}")
        print(f"日志级别: {LOG_LEVEL}")
        print("=" * 50)


if __name__ == "__main__":
    Config.print_config()
