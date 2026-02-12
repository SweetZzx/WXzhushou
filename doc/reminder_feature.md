# 日程提醒功能技术文档（新手版）

## 一、功能介绍

### 这个功能是做什么的？

想象一下，你有一个智能助手，它会在以下情况主动给你发微信消息：

1. **每天早上8点**：告诉你今天有哪些日程安排
2. **每个日程开始前10分钟**：提醒你"嘿，你的会议马上要开始了！"

这就是我们的日程提醒功能！

### 举个实际的例子

```
【场景1：每天早上8点】
你收到一条微信消息：

📅 早上好！今天是 2月12日 周三

您今天有 2 个日程安排：

1. 09:30 - 晨会
2. 14:00 - 项目评审

祝您今天愉快！🎉

---

【场景2：会议开始前10分钟】
你收到另一条微信消息：

⏰ 日程提醒

📅 项目评审
🕐 14:00 开始
⏱️ 还有 10 分钟
```

---

## 二、系统是怎么工作的？（简单版）

### 整体流程图

```
┌────────────────────────────────────────────────────────────────┐
│                         你的微信                                │
│                    （收到提醒消息）                              │
└────────────────────────────▲───────────────────────────────────┘
                             │
                             │ 微信服务器帮我们送达消息
                             │
┌────────────────────────────┴───────────────────────────────────┐
│                      我们的服务器                                │
│                       (47.110.242.66)                          │
│                                                                │
│  ┌──────────────┐   ┌──────────────┐   ┌──────────────┐       │
│  │   定时器      │   │   数据库      │   │  微信推送    │       │
│  │  (闹钟功能)   │   │ (存储日程)    │   │  (发消息)    │       │
│  └──────────────┘   └──────────────┘   └──────────────┘       │
│         │                  │                  │                │
│         └──────────────────┼──────────────────┘                │
│                            │                                   │
│                    ┌───────▼───────┐                           │
│                    │   主程序      │                           │
│                    │  (协调工作)   │                           │
│                    └───────────────┘                           │
└────────────────────────────────────────────────────────────────┘
```

### 用大白话解释

1. **定时器**：就像你手机的闹钟，到了设定的时间就会"响"
2. **数据库**：就像一个笔记本，记录着你添加的所有日程
3. **微信推送**：就像一个快递员，把消息送到你的微信上
4. **主程序**：就像一个指挥官，协调上面三个部分一起工作

---

## 三、详细架构说明

### 3.1 目录结构

```
WXzhushou/
├── services/                      # 服务目录（核心功能代码）
│   ├── reminder_service.py        # 🔔 提醒服务（定时任务）
│   ├── wechat_push_service.py     # 📱 微信推送服务
│   ├── agent_service.py           # 🤖 AI对话服务
│   └── schedule_service.py        # 📅 日程管理服务
│
├── models/                        # 数据模型目录
│   ├── schedule.py                # 日程数据表结构
│   └── user_settings.py           # 用户设置表结构
│
├── database/                      # 数据库目录
│   ├── session.py                 # 数据库连接管理
│   └── base.py                    # 数据库基础配置
│
├── app/
│   ├── server.py                  # 主服务器入口
│   └── routers/
│       └── wechat.py              # 微信消息路由
│
├── doc/                           # 文档目录
│   └── reminder_feature.md        # 本文档
│
├── data/                          # 数据目录
│   └── wechat.db                  # SQLite数据库文件
│
├── .env                           # 环境配置文件
├── requirements.txt               # Python依赖包列表
└── main.py                        # 程序启动入口
```

### 3.2 核心文件详解

#### 文件1：reminder_service.py（提醒服务）

**这个文件是做什么的？**
这是整个提醒功能的"大脑"，负责：
- 设置定时任务（每天8点、每分钟检查）
- 判断什么时候该发提醒
- 调用微信推送服务发送消息

**核心代码解析**：

```python
# 第1步：创建一个定时器
from apscheduler.schedulers.asyncio import AsyncIOScheduler

class ReminderService:
    def __init__(self):
        # 初始化定时器，设置时区为上海时间
        self.scheduler = AsyncIOScheduler(timezone="Asia/Shanghai")

    async def start(self):
        """启动定时任务"""

        # 任务1：每天19:10执行每日提醒
        self.scheduler.add_job(
            self.send_daily_reminders,           # 要执行的函数
            CronTrigger(hour=19, minute=10),     # 执行时间：每天19:10
            id="daily_reminder",                  # 任务ID
        )

        # 任务2：每分钟检查一次是否需要发送日程前提醒
        self.scheduler.add_job(
            self.check_pre_schedule_reminders,   # 要执行的函数
            IntervalTrigger(minutes=1),          # 执行间隔：每1分钟
            id="pre_schedule_check",             # 任务ID
        )

        # 启动定时器
        self.scheduler.start()
```

**每日提醒是怎么实现的？**

```python
async def send_daily_reminders(self):
    """每天固定时间执行，发送今日日程汇总"""

    # 第1步：从数据库获取今天有日程的用户
    # SQL相当于：SELECT DISTINCT user_id FROM schedules WHERE 日期=今天

    # 第2步：对每个用户
    for user_id in user_ids:
        # 检查用户是否开启了每日提醒
        if not user_settings.daily_reminder_enabled:
            continue  # 用户关闭了，跳过

        # 获取用户今天的所有日程
        # 构建消息内容
        message = f"📅 早上好！今天是 {today_str}\n\n"
        message += f"您今天有 {len(schedules)} 个日程安排：\n\n"
        for schedule in schedules:
            message += f"{time} - {title}\n"

        # 第3步：发送消息
        await wechat_push_service.send_text_message(user_id, message)
```

**日程前提醒是怎么实现的？**

```python
async def check_pre_schedule_reminders(self):
    """每分钟执行一次，检查是否有日程即将开始"""

    now = datetime.now()

    # 查找1-11分钟后开始的日程
    check_start = now + timedelta(minutes=1)
    check_end = now + timedelta(minutes=11)

    # 从数据库查询
    schedules = 查询在check_start到check_end之间开始的日程

    for schedule in schedules:
        # 计算还有多少分钟开始
        minutes_left = (schedule.scheduled_time - now).total_seconds() / 60

        # 如果剩余时间 <= 10分钟，发送提醒
        if minutes_left <= 10:
            # 检查是否已经发过（避免重复）
            # 发送提醒消息
            await wechat_push_service.send_text_message(user_id, message)
```

---

#### 文件2：wechat_push_service.py（微信推送服务）

**这个文件是做什么的？**
负责和微信服务器"对话"，把消息送到用户微信上。

**工作原理图**：

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│  我们的服务器 │────▶│  微信服务器  │────▶│  用户微信   │
│             │     │             │     │             │
│ 发送消息请求 │     │ 转发消息    │     │ 收到消息    │
└─────────────┘     └─────────────┘     └─────────────┘
```

**核心代码解析**：

```python
class WeChatPushService:
    async def get_access_token(self):
        """
        获取微信API的"入场券"

        微信API需要一个access_token才能调用，
        就像进入大楼需要门禁卡一样。
        """
        url = f"https://api.weixin.qq.com/cgi-bin/token"
        params = {
            "grant_type": "client_credential",
            "appid": self.app_id,
            "secret": self.app_secret
        }

        # 发送请求获取token
        response = await httpx.get(url, params=params)
        data = response.json()

        # token有效期7200秒（2小时）
        self._access_token = data["access_token"]
        return self._access_token

    async def send_text_message(self, user_id, content):
        """
        发送文本消息给用户

        参数：
            user_id: 用户的微信OpenID（唯一标识）
            content: 要发送的消息内容
        """
        # 先获取token
        access_token = await self.get_access_token()

        # 构建请求
        url = f"https://api.weixin.qq.com/cgi-bin/message/custom/send"
        payload = {
            "touser": user_id,          # 发给谁
            "msgtype": "text",          # 消息类型：文本
            "text": {
                "content": content      # 消息内容
            }
        }

        # 发送请求
        response = await httpx.post(url, json=payload)
        result = response.json()

        # 检查是否成功
        if result.get("errcode") == 0:
            return True   # 发送成功！
        else:
            return False  # 发送失败，查看错误码
```

**常见错误码说明**：

| 错误码 | 含义 | 解决方法 |
|-------|------|---------|
| 0 | 成功 | 无需处理 |
| 40001 | token无效 | 重新获取token |
| 45015 | 用户48小时内未互动 | 让用户先发一条消息 |
| 45047 | 客服消息下行超过限制 | 等待用户主动发消息 |

---

#### 文件3：user_settings.py（用户设置模型）

**这个文件是做什么的？**
定义用户个性化设置的数据结构，存储在数据库中。

**数据库表结构**：

```python
class UserSettings(Base):
    __tablename__ = "user_settings"  # 表名

    # 字段定义
    id = 主键
    user_id = 用户微信ID

    # 每日提醒设置
    daily_reminder_enabled = 是否开启每日提醒（True/False）
    daily_reminder_time = 每日提醒时间（如"08:00"）

    # 日程前提醒设置
    pre_schedule_reminder_enabled = 是否开启日程前提醒（True/False）
    pre_schedule_reminder_minutes = 提前多少分钟提醒（如10）
```

**数据库实际存储的样子**：

| id | user_id | daily_reminder_enabled | daily_reminder_time | pre_schedule_reminder_enabled | pre_schedule_reminder_minutes |
|----|---------|----------------------|---------------------|------------------------------|------------------------------|
| 1 | oKXgA... | True | 08:00 | True | 10 |
| 2 | abc12... | False | 08:00 | True | 15 |

---

## 四、从用户发送消息到收到提醒的完整流程

### 场景：用户添加一个日程

```
用户操作：在微信中发送"明天下午3点开会"

┌─────────────────────────────────────────────────────────────────┐
│ 第1步：微信服务器把消息转发到我们的服务器                          │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│ 第2步：我们的服务器接收消息                                       │
│        - wechat.py 解析XML消息                                   │
│        - 提取用户ID和消息内容                                     │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│ 第3步：AI分析消息                                                 │
│        - agent_service.py 调用智谱AI                             │
│        - AI判断用户想要"创建日程"                                 │
│        - 提取：标题=开会，时间=明天15:00                          │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│ 第4步：保存到数据库                                               │
│        - schedule_service.py 执行                                │
│        - INSERT INTO schedules (user_id, title, time...)        │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│ 第5步：回复用户                                                   │
│        - 返回"日程创建成功！明天15:00 开会"                       │
└─────────────────────────────────────────────────────────────────┘
```

### 场景：定时提醒触发

```
时间到达：每天08:00

┌─────────────────────────────────────────────────────────────────┐
│ 第1步：定时器触发                                                 │
│        - APScheduler 检测到时间到了                              │
│        - 调用 send_daily_reminders() 函数                        │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│ 第2步：查询数据库                                                 │
│        - 查找今天有日程的所有用户                                 │
│        - SELECT DISTINCT user_id FROM schedules WHERE date=今天 │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│ 第3步：为每个用户构建消息                                         │
│        - 查询用户今天的所有日程                                   │
│        - 组装消息文本                                             │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│ 第4步：发送消息                                                   │
│        - wechat_push_service.py 获取access_token                 │
│        - 调用微信客服消息API                                      │
│        - POST https://api.weixin.qq.com/cgi-bin/message/...     │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│ 第5步：用户收到消息                                               │
│        - 微信服务器推送消息到用户手机                             │
│        - 用户看到"📅 早上好！..."                                 │
└─────────────────────────────────────────────────────────────────┘
```

---

## 五、如何修改和扩展

### 5.1 修改每日提醒时间

**方法1：直接修改代码**

打开 `services/reminder_service.py`，找到：

```python
CronTrigger(hour=19, minute=10)  # 当前是19:10
```

改成你想要的时间，比如早上8点：

```python
CronTrigger(hour=8, minute=0)  # 改成08:00
```

**方法2：通过对话修改**（开发中）

在微信中发送："把每日提醒改到早上7点"

### 5.2 修改日程前提醒时间

当前是提前10分钟提醒，要改成15分钟：

打开 `services/reminder_service.py`，找到检查逻辑：

```python
if minutes_left <= user_settings.pre_schedule_reminder_minutes:
```

这里已经是根据用户设置来的，所以只需要让用户发送：
"把日程提醒改成提前15分钟"

### 5.3 添加新的提醒类型

比如你想添加"每周一早上发送本周日程汇总"：

```python
async def start(self):
    # ... 现有代码 ...

    # 新增：每周一08:00发送本周汇总
    self.scheduler.add_job(
        self.send_weekly_summary,           # 新写的函数
        CronTrigger(day_of_week='mon', hour=8, minute=0),
        id="weekly_summary",
    )

async def send_weekly_summary(self):
    """发送本周日程汇总"""
    # 获取本周的日程
    # 构建消息
    # 发送消息
    pass
```

---

## 六、常见问题解答

### Q1: 为什么我收不到提醒？

**可能的原因和解决方法**：

1. **今天没有日程**
   - 每日提醒只会发给当天有日程的用户
   - 解决：先添加一个今天的日程

2. **用户48小时内没有和公众号互动**
   - 微信限制了只能给48小时内互动过的用户发消息
   - 解决：先给公众号发一条消息

3. **提醒功能被关闭**
   - 检查设置：发送"查看提醒设置"

4. **服务器时间不对**
   - 检查服务器时区是否是 Asia/Shanghai

### Q2: 如何查看日志排查问题？

SSH登录服务器后执行：

```bash
# 查看最近的日志
tail -50 /opt/wxzhushou/app.log

# 实时查看日志
tail -f /opt/wxzhushou/app.log

# 搜索提醒相关日志
grep "提醒\|reminder\|推送" /opt/wxzhushou/app.log
```

### Q3: 如何手动测试推送？

```bash
# 调用测试接口
curl -X POST http://47.110.242.66:8000/test/push
```

### Q4: 数据库文件在哪里？

```
/opt/wxzhushou/data/wechat.db
```

可以用SQLite工具查看：

```bash
sqlite3 /opt/wxzhushou/data/wechat.db
sqlite> SELECT * FROM schedules;
sqlite> SELECT * FROM user_settings;
```

---

## 七、依赖库说明

在 `requirements.txt` 中，与提醒功能相关的依赖：

```txt
# 定时任务调度器
apscheduler==3.10.4

# 异步HTTP客户端（调用微信API）
httpx==0.25.1

# 异步数据库支持
aiosqlite==0.19.0
sqlalchemy==2.0.23
```

**安装依赖**：

```bash
pip install -r requirements.txt
```

---

## 八、总结

### 核心要点回顾

1. **APScheduler** 负责定时任务（闹钟功能）
2. **SQLite** 存储日程和用户设置（笔记本）
3. **httpx** 调用微信API（快递员）
4. **异步编程** 提高并发性能（同时处理多个任务）

### 消息流向

```
用户 → 微信服务器 → 我们的服务器 → AI处理 → 数据库存储
                                              ↓
用户 ← 微信服务器 ← 我们的服务器 ← 定时触发 ← 定时器
```

### 下一步可以做什么

1. 添加更多提醒类型（周汇总、月汇总）
2. 支持用户自定义提醒时间
3. 添加提醒模板（不同的消息样式）
4. 支持多条提醒合并（避免消息轰炸）

---

## 附录：API参考

### 微信客服消息API

**文档地址**：https://developers.weixin.qq.com/doc/offiaccount/Message_Management/Service_Center_messages.html

**发送文本消息**：

```http
POST https://api.weixin.qq.com/cgi-bin/message/custom/send?access_token=ACCESS_TOKEN

{
    "touser": "OPENID",
    "msgtype": "text",
    "text": {
        "content": "消息内容"
    }
}
```

### APScheduler文档

**文档地址**：https://apscheduler.readthedocs.io/

**常用触发器**：

```python
# 定时触发（如每天8点）
CronTrigger(hour=8, minute=0)

# 间隔触发（如每5分钟）
IntervalTrigger(minutes=5)

# 一次性触发（指定时间）
DateTrigger(run_date='2024-02-12 08:00:00')
```

---

*文档版本：1.0*
*最后更新：2026-02-12*
*作者：Claude AI Assistant*
