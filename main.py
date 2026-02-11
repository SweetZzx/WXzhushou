"""
微信AI助手 - 主入口文件
"""
import uvicorn
from dotenv import load_dotenv
import sys
from pathlib import Path
import os

# 加载环境变量
load_dotenv()

# 添加项目根目录到Python路径
sys.path.insert(0, str(Path(__file__).parent))

from config import Config, SERVER_HOST, SERVER_PORT, SERVER_RELOAD, DATA_DIR
from app.server import app


def ensure_data_dir():
    """确保数据目录存在"""
    os.makedirs(DATA_DIR, exist_ok=True)


def main():
    """主函数"""
    # 验证配置
    if not Config.validate():
        print("配置验证失败，请检查环境变量设置")
        return

    # 确保数据目录存在
    ensure_data_dir()

    # 打印配置信息
    Config.print_config()

    # 启动服务器
    print("\n" + "=" * 50)
    print("正在启动微信AI助手服务器...")
    print("=" * 50 + "\n")

    uvicorn.run(
        "main:app",
        host=SERVER_HOST,
        port=SERVER_PORT,
        reload=SERVER_RELOAD,
        log_level="info"
    )


if __name__ == "__main__":
    main()
