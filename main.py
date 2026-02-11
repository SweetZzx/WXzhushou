"""
微信AI助手 - 主入口文件
"""
import uvicorn
from dotenv import load_dotenv
import sys
from pathlib import Path

# 加载环境变量
load_dotenv()

# 添加项目根目录到Python路径
sys.path.insert(0, str(Path(__file__).parent))

from config import Config, SERVER_HOST, SERVER_PORT, SERVER_RELOAD
from app.server import app


def main():
    """主函数"""
    # 验证配置
    if not Config.validate():
        print("配置验证失败，请检查环境变量设置")
        return

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
