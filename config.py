"""
配置文件
从环境变量读取配置，提供统一的配置访问
"""
import os
from pathlib import Path

# 项目根目录
BASE_DIR = Path(__file__).parent

# ============================================
# 微信配置
# ============================================
WECHAT_APP_ID: str = os.getenv("WECHAT_APP_ID", "")
WECHAT_APP_SECRET: str = os.getenv("WECHAT_APP_SECRET", "")
WECHAT_TOKEN: str = os.getenv("WECHAT_TOKEN", "")
WECHAT_ENCODING_AES_KEY: str = os.getenv("WECHAT_ENCODING_AES_KEY", "")
WECHAT_MODE: str = os.getenv("WECHAT_MODE", "normal")

# ============================================
# 智谱 AI 配置
# ============================================
ZHIPU_API_KEY: str = os.getenv("ZHIPU_API_KEY", "")
ZHIPU_API_BASE: str = os.getenv("ZHIPU_API_BASE", "https://open.bigmodel.cn/api/paas/v4")
ZHIPU_MODEL: str = os.getenv("ZHIPU_MODEL", "glm-4-air")
ZHIPU_TEMPERATURE: float = float(os.getenv("ZHIPU_TEMPERATURE", "0.7"))
ZHIPU_MAX_TOKENS: int = int(os.getenv("ZHIPU_MAX_TOKENS", "2000"))
ZHIPU_TIMEOUT: int = int(os.getenv("ZHIPU_TIMEOUT", "30"))

# ============================================
# LangSmith 配置（追踪调试）
# ============================================
LANGCHAIN_TRACING_V2: bool = os.getenv("LANGCHAIN_TRACING_V2", "false").lower() == "true"
LANGCHAIN_API_KEY: str = os.getenv("LANGCHAIN_API_KEY", "")
LANGCHAIN_PROJECT: str = os.getenv("LANGCHAIN_PROJECT", "wxzhushou")

# ============================================
# 服务器配置
# ============================================
SERVER_HOST: str = os.getenv("SERVER_HOST", "0.0.0.0")
SERVER_PORT: int = int(os.getenv("SERVER_PORT", "8000"))
SERVER_RELOAD: bool = os.getenv("SERVER_RELOAD", "false").lower() == "true"

# ============================================
# 数据配置
# ============================================
DATA_DIR: str = os.getenv("DATA_DIR", str(BASE_DIR / "data"))
DATABASE_URL: str = os.getenv("DATABASE_URL", f"sqlite+aiosqlite:///{DATA_DIR}/wechat.db")

# ============================================
# 日志配置
# ============================================
LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")
LOG_FILE: str = os.getenv("LOG_FILE", f"{DATA_DIR}/logs/app.log")

# ============================================
# 对话配置
# ============================================
DEFAULT_SYSTEM_PROMPT: str = os.getenv(
    "DEFAULT_SYSTEM_PROMPT",
    "你是一个友好、乐于助人的AI助手。"
)
CONTEXT_MEMORY_SIZE: int = int(os.getenv("CONTEXT_MEMORY_SIZE", "10"))
WECHAT_REPLY_TIMEOUT: int = int(os.getenv("WECHAT_REPLY_TIMEOUT", "4"))

# ============================================
# 加密配置
# ============================================
# 联系人数据加密密钥（32字节，用于AES-256）
# 生成方式: python -c "import secrets; print(secrets.token_hex(16))"
CONTACT_ENCRYPT_KEY: str = os.getenv("CONTACT_ENCRYPT_KEY", "contact_encrypt_key_32bytes!")


class Config:
    """配置管理类"""

    @staticmethod
    def validate() -> bool:
        """验证必需的配置项"""
        errors = []

        if not WECHAT_APP_ID:
            errors.append("WECHAT_APP_ID 未设置")
        if not WECHAT_APP_SECRET:
            errors.append("WECHAT_APP_SECRET 未设置")
        if not WECHAT_TOKEN:
            errors.append("WECHAT_TOKEN 未设置")
        if not ZHIPU_API_KEY:
            errors.append("ZHIPU_API_KEY 未设置")

        if errors:
            for error in errors:
                print(f"❌ {error}")
            return False
        return True

    @staticmethod
    def print_config() -> None:
        """打印配置信息（隐藏敏感信息）"""
        print("=" * 50)
        print("微信AI助手配置")
        print("=" * 50)

        # 微信配置
        print("【微信配置】")
        print(f"  APP ID: {WECHAT_APP_ID[:8]}...{WECHAT_APP_ID[-4:] if WECHAT_APP_ID else '未设置'}")
        print(f"  Token: {WECHAT_TOKEN}")

        # 智谱配置
        print("【智谱 AI】")
        print(f"  API Key: {ZHIPU_API_KEY[:8]}...{ZHIPU_API_KEY[-4:] if ZHIPU_API_KEY else '未设置'}")
        print(f"  模型: {ZHIPU_MODEL}")

        # LangSmith 配置
        print("【LangSmith】")
        print(f"  追踪: {'✅ 已启用' if LANGCHAIN_TRACING_V2 else '❌ 未启用'}")
        print(f"  项目: {LANGCHAIN_PROJECT}")

        # 服务器配置
        print("【服务器】")
        print(f"  地址: {SERVER_HOST}:{SERVER_PORT}")

        print("=" * 50)


if __name__ == "__main__":
    Config.print_config()
