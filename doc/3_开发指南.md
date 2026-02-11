# 微信AI助手 - 服务器开发指南

> 本文档用于服务器端开发参考，请在SSH连接后查阅。

## 快速开始

### 连接服务器
```bash
ssh wechat-server
# 或直接使用IP
ssh root@47.110.242.66
```

### 进入项目目录
```bash
cd /root/WXzhushou
```

## 项目结构

```
/root/WXzhushou/
├── main.py                 # 应用入口
├── config.py               # 配置文件
├── requirements.txt        # 依赖包列表
├── .env                   # 环境变量配置
│
├── app/
│   ├── server.py          # FastAPI服务器
│   └── routers/
│       └── wechat.py      # 微信路由
│
├── services/
│   ├── wechat_service.py  # 微信消息处理
│   └── ai_service.py      # AI对话服务
│
├── models/                # 数据模型
└── utils/                 # 工具模块
```

## 常用命令

### 虚拟环境
```bash
# 激活虚拟环境
source venv/bin/activate

# 退出虚拟环境
deactivate

# 安装新依赖
pip install xxx

# 导出依赖
pip freeze > requirements.txt
```

### 服务管理
```bash
# 启动服务
systemctl start wechat-ai.service

# 停止服务
systemctl stop wechat-ai.service

# 重启服务
systemctl restart wechat-ai.service

# 查看状态
systemctl status wechat-ai.service

# 实时日志
journalctl -u wechat-ai.service -f

# 最近50行日志
journalctl -u wechat-ai.service -n 50
```

### 手动运行（调试用）
```bash
# 激活虚拟环境后
source venv/bin/activate
python main.py

# 或直接使用虚拟环境的Python
./venv/bin/python main.py
```

### 查看日志
```bash
# 应用日志
tail -f data/logs/app.log

# 最近50行
tail -50 data/logs/app.log
```

## 开发流程

### 1. 修改代码
```bash
# 使用VSCode Remote-SSH编辑文件
# 修改后自动保存到服务器
```

### 2. 重启服务
```bash
systemctl restart wechat-ai.service
```

### 3. 验证修改
```bash
# 检查服务状态
systemctl status wechat-ai.service

# 查看日志
journalctl -u wechat-ai.service -n 20

# 测试接口
curl http://localhost:8000/health
```

## 配置说明

### 环境变量 (.env)
```bash
# 查看配置
cat .env

# 编辑配置
nano .env
# 或
vi .env

# 修改后重启服务
systemctl restart wechat-ai.service
```

### 关键配置项
| 配置项 | 当前值 | 说明 |
|-------|-------|------|
| WECHAT_TOKEN | 135935 | 微信验证Token |
| ZHIPU_API_KEY | f9442f7d... | 智谱AI密钥 |
| SERVER_PORT | 8000 | 服务端口 |

## 调试技巧

### 查看实时日志
```bash
# systemd日志
journalctl -u wechat-ai.service -f

# 应用日志
tail -f data/logs/app.log
```

### 测试微信验证接口
```bash
# 手动测试验证逻辑
curl "http://localhost:8000/wechat?signature=xxx&timestamp=xxx&nonce=xxx&echostr=test"
```

### 检查端口占用
```bash
netstat -tuln | grep 8000
# 或
lsof -i:8000
```

### 查看进程
```bash
ps aux | grep main.py
```

## 故障排查

### 服务无法启动
```bash
# 1. 检查Python语法
python -m py_compile main.py

# 2. 查看详细错误
journalctl -u wechat-ai.service -n 50 --no-pager

# 3. 手动运行查看错误
cd /root/WXzhushou
./venv/bin/python main.py
```

### 微信验证失败
```bash
# 1. 检查Token配置
grep WECHAT_TOKEN .env

# 2. 查看验证日志
journalctl -u wechat-ai.service | grep "验证"
```

### AI无响应
```bash
# 1. 检查API密钥
grep ZHIPU_API_KEY .env

# 2. 查看AI服务日志
journalctl -u wechat-ai.service | grep "AI"
```

## 防火墙配置

```bash
# 查看防火墙状态
ufw status

# 开放端口
ufw allow 8000/tcp

# 或使用iptables
iptables -I INPUT -p tcp --dport 8000 -j ACCEPT
```

## 外网地址

- **服务器IP**: 47.110.242.66
- **服务端口**: 8000
- **微信接口**: http://47.110.242.66:8000/wechat

⚠️ **注意**: 需在阿里云安全组中开放8000端口

## 快捷别名（可选）

在 ~/.bashrc 中添加：
```bash
alias wx='cd /root/WXzhushou'
alias wx-log='journalctl -u wechat-ai.service -f'
alias wx-restart='systemctl restart wechat-ai.service'
alias wx-status='systemctl status wechat-ai.service'
```

执行 `source ~/.bashrc` 生效。

## 更新代码

从本地上传修改：
```bash
# 在本地执行
scp app/routers/wechat.py wechat-server:/root/WXzhushou/app/routers/
```

或在VSCode中保存后自动同步。

---

**最后更新**: 2026-02-11
