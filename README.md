# 微信AI助手

> 基于智谱GLM大模型的微信智能助手机器人

[![FastAPI](https://img.shields.io/badge/FastAPI-0.104.1-green)](https://fastapi.tiangolo.com)
[![Python](https://img.shields.io/badge/Python-3.8+-blue)](https://www.python.org)
[![License](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

## ✨ 功能特性

- 🤖 **智能对话**: 集成智谱GLM-4大模型，支持自然语言交互
- 💬 **微信集成**: 完美对接微信公众平台测试号
- 🧠 **对话记忆**: 支持多轮对话上下文管理
- 👥 **多用户**: 独立的用户会话管理
- 📝 **日志系统**: 完善的请求日志记录

## 🚀 快速开始

### 环境要求

- Python 3.8+
- pip

### 安装依赖

```bash
pip install -r requirements.txt
```

### 配置环境变量

编辑 `.env` 文件：

```env
# 微信配置
WECHAT_TOKEN=135935
WECHAT_APP_ID=your_app_id
WECHAT_APP_SECRET=your_app_secret

# 智谱AI配置
ZHIPU_API_KEY=your_api_key
ZHIPU_MODEL=glm-4
```

### 启动服务

```bash
python main.py
```

服务将在 `http://0.0.0.0:8000` 启动。

## 📁 项目结构

```
WXzhushou/
├── main.py                 # 应用入口
├── config.py               # 配置管理
├── requirements.txt        # 依赖列表
├── .env                   # 环境变量
│
├── app/                   # Web应用
│   ├── server.py          # FastAPI服务器
│   └── routers/
│       └── wechat.py      # 微信路由
│
├── services/              # 业务服务
│   ├── ai_service.py      # AI对话服务
│   └── wechat_service.py  # 微信消息处理
│
├── models/                # 数据模型
├── utils/                 # 工具模块
└── doc/                   # 项目文档
    ├── PROJECT_ARCHIVE.md      # 项目归档
    ├── SERVER_DEV_GUIDE.md     # 开发指南
    └── PROJECT_PLAN.md         # 项目规划
```

## 🔗 API接口

| 接口 | 方法 | 说明 |
|------|------|------|
| `/health` | GET | 健康检查 |
| `/wechat` | GET | 微信服务器验证 |
| `/wechat` | POST | 微信消息接收 |

## 📚 文档

详细文档请查看 [doc/](./doc/) 目录：

- **[项目归档](./doc/PROJECT_ARCHIVE.md)** - 完整的项目总结和技术文档
- **[开发指南](./doc/SERVER_DEV_GUIDE.md)** - 服务器部署和开发说明
- **[项目规划](./doc/PROJECT_PLAN.md)** - 功能设计和开发路线

## 🌐 在线体验

- **服务器**: http://47.110.242.66:8000
- **微信接口**: http://47.110.242.66:8000/wechat
- **状态**: ✅ 运行中

## 🛠️ 开发

### 本地开发

```bash
# 克隆项目
git clone <repository-url>

# 安装依赖
pip install -r requirements.txt

# 配置环境变量
cp .env.example .env

# 启动开发服务器
python main.py
```

### 服务器部署

```bash
# SSH连接服务器
ssh root@47.110.242.66

# 进入项目目录
cd /opt/wxzhushou

# 重启服务
systemctl restart wechat-ai.service

# 查看日志
journalctl -u wechat-ai.service -f
```

## 🎯 后续计划

- [ ] 对话持久化存储
- [ ] 用户画像管理
- [ ] 自定义命令系统
- [ ] 图片识别功能
- [ ] 语音消息支持
- [ ] Web管理后台

## 📄 许可证

MIT License

## 👥 贡献

欢迎提交 Issue 和 Pull Request！

---

**项目状态**: ✅ 第一阶段完成
**最后更新**: 2026-02-11
**版本**: v1.0.0-alpha
