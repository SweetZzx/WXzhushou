# LangChain 1.2 重构计划

> **文档版本**: v1.0
> **创建日期**: 2026-02-24
> **预计工期**: 3-5 天
> **重构目标**: 将项目从自研 Agent 迁移到 LangChain 1.2 + LangGraph 架构

---

## 一、重构背景

### 1.1 当前问题

| 问题 | 描述 | 影响 |
|-----|------|------|
| 非 LangChain 架构 | 只借用了 LangChain 的记忆模块，核心 Agent 是自研的 | 简历上不能说"基于 LangChain" |
| 代码重复 | 工具定义散落在多个地方 | 维护困难 |
| 缺乏标准化 | 没有使用业界标准的 Agent 框架 | 技术栈不够主流 |

### 1.2 重构收益

- ✅ 真正基于 LangChain 1.2 框架，简历加分
- ✅ 使用 LangGraph 进行状态管理，官方推荐方案
- ✅ 对话历史持久化到 SQLite
- ✅ 统一使用 `uv` 管理项目依赖
- ✅ 便于后续切换模型（ChatOpenAI 兼容）

---

## 二、技术选型

### 2.1 核心技术栈

| 组件 | 技术选型 | 版本 | 说明 |
|-----|---------|------|------|
| 包管理 | uv | latest | 快速、现代的 Python 包管理器 |
| Agent 框架 | LangChain | 1.2.x | 主流 LLM 应用框架 |
| 状态管理 | LangGraph | 1.0.x | LangChain 官方状态管理 |
| 对话持久化 | langgraph-checkpoint-sqlite | 2.0.x | SQLite 持久化 |
| LLM | ChatOpenAI (智谱兼容) | - | 便于切换模型 |
| 异步数据库 | aiosqlite | 0.20.x | 异步 SQLite |
| Web 框架 | FastAPI | 0.115.x | 保持不变 |

### 2.2 数据库方案

**继续使用 SQLite**，原因：

| 因素 | PostgreSQL | SQLite | 结论 |
|-----|-----------|--------|------|
| 服务器内存 | 需要 4GB+ | 几乎不占 | SQLite ✅ |
| 并发性能 | 高 | 中等（够用） | SQLite ✅ |
| 运维成本 | 高 | 低 | SQLite ✅ |
| 适用场景 | 多应用 | 单应用 | SQLite ✅ |

### 2.3 架构图

```
┌─────────────────────────────────────────────────────────────┐
│                       微信服务器                             │
└─────────────────────────┬───────────────────────────────────┘
                          │ XML 消息
                          ▼
┌─────────────────────────────────────────────────────────────┐
│                    FastAPI 应用                              │
│                   app/routers/wechat.py                     │
└─────────────────────────┬───────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────────┐
│                 LangGraph Agent Service                     │
│               services/langchain_agent.py                   │
│  ┌─────────────────────────────────────────────────────┐   │
│  │                    StateGraph                        │   │
│  │  ┌─────────┐    ┌─────────┐    ┌─────────┐         │   │
│  │  │  START  │ -> │  Agent  │ -> │   END   │         │   │
│  │  └─────────┘    └────┬────┘    └─────────┘         │   │
│  │                      │                              │   │
│  │                      ▼                              │   │
│  │              ┌──────────────┐                       │   │
│  │              │    Tools     │                       │   │
│  │              │  (日程管理)   │                       │   │
│  │              └──────────────┘                       │   │
│  └─────────────────────────────────────────────────────┘   │
│                                                             │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐      │
│  │ ChatOpenAI   │  │ SqliteSaver  │  │   System     │      │
│  │  (智谱 GLM)   │  │ (对话持久化)  │  │   Prompt     │      │
│  └──────────────┘  └──────────────┘  └──────────────┘      │
└─────────────────────────┬───────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────────┐
│                   业务服务层（保持不变）                      │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐      │
│  │schedule_svc  │  │reminder_svc  │  │  asr_svc     │      │
│  │  (日程CRUD)  │  │  (提醒服务)   │  │  (语音识别)  │      │
│  └──────────────┘  └──────────────┘  └──────────────┘      │
└─────────────────────────┬───────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────────┐
│                     数据层                                   │
│  ┌──────────────────────┐  ┌──────────────────────┐        │
│  │   schedules.db       │  │  checkpoints.db      │        │
│  │   (日程数据)          │  │  (LangGraph 状态)    │        │
│  │   SQLite + aiosqlite │  │  SqliteSaver         │        │
│  └──────────────────────┘  └──────────────────────┘        │
└─────────────────────────────────────────────────────────────┘
```

---

## 三、文件变更清单

### 3.1 新建文件

| 文件 | 用途 | 优先级 |
|-----|------|--------|
| `pyproject.toml` | uv 项目配置 | P0 |
| `uv.lock` | 依赖锁定（自动生成） | P0 |
| `services/langchain_agent.py` | LangGraph Agent 服务 | P0 |
| `services/langchain_tools.py` | LangChain 工具定义 | P0 |
| `services/langchain_llm.py` | LLM 封装（智谱兼容） | P0 |

### 3.2 修改文件

| 文件 | 变更内容 | 优先级 |
|-----|---------|--------|
| `app/routers/wechat.py` | 调用新 Agent 服务 | P0 |
| `config.py` | 新增 LangChain 相关配置 | P0 |
| `database/session.py` | 优化数据库连接 | P1 |
| `main.py` | 启动逻辑调整 | P1 |

### 3.3 删除文件

| 文件 | 原因 |
|-----|------|
| `services/agent_service.py` | 被新 Agent 服务替代 |
| `requirements.txt` | 改用 pyproject.toml |

### 3.4 保留文件（不变）

| 文件/目录 | 说明 |
|----------|------|
| `services/schedule_service.py` | 日程 CRUD 服务 |
| `services/reminder_service.py` | 提醒服务 |
| `services/wechat_service.py` | 微信消息解析 |
| `services/wechat_push_service.py` | 微信推送服务 |
| `services/asr_service.py` | 语音识别服务 |
| `utils/time_parser.py` | 时间解析工具 |
| `models/` | 数据模型 |
| `database/` | 数据库配置 |

---

## 四、依赖包变更

### 4.1 新增依赖

```toml
# pyproject.toml

[project]
name = "wxzhushou"
version = "3.0.0"
description = "基于 LangChain 的微信智能日程助手"
requires-python = ">=3.11"

dependencies = [
    # Web 框架
    "fastapi>=0.115.0",
    "uvicorn>=0.32.0",
    "httpx>=0.28.0",

    # LangChain 核心
    "langchain>=1.2.0",
    "langchain-openai>=1.1.0",
    "langchain-community>=1.3.0",

    # LangGraph 状态管理
    "langgraph>=1.0.0",
    "langgraph-checkpoint-sqlite>=2.0.0",

    # 数据库
    "aiosqlite>=0.20.0",
    "sqlalchemy>=2.0.0",

    # 智谱 AI
    "zhipuai>=2.1.0",

    # 定时任务
    "apscheduler>=3.11.0",

    # 工具
    "python-dotenv>=1.0.0",
    "pydantic>=2.10.0",
    "pydantic-settings>=2.6.0",
]

[project.optional-dependencies]
dev = [
    "pytest>=8.0.0",
    "pytest-asyncio>=0.24.0",
    "black>=24.0.0",
    "ruff>=0.8.0",
]
```

### 4.2 移除依赖

| 包名 | 原因 |
|-----|------|
| `zai` | 智谱旧版 SDK，改用 zhipuai + ChatOpenAI |
| `langchain-core` | 由 langchain 自动包含 |
| `langchain-community` | 版本升级 |

---

## 五、核心代码设计

### 5.1 LLM 封装 (`services/langchain_llm.py`)

```python
"""
LLM 封装模块
使用 ChatOpenAI 兼容接口，便于切换模型
"""
import os
from langchain_openai import ChatOpenAI
from config import ZHIPU_API_KEY

# 智谱 GLM 模型配置
ZHIPU_API_BASE = "https://open.bigmodel.cn/api/paas/v4"
DEFAULT_MODEL = "glm-4"


def get_llm(model: str = None, temperature: float = 0.7, **kwargs) -> ChatOpenAI:
    """
    获取 LLM 实例

    Args:
        model: 模型名称，默认 glm-4
        temperature: 温度参数
        **kwargs: 其他 ChatOpenAI 参数

    Returns:
        ChatOpenAI 实例
    """
    return ChatOpenAI(
        model=model or DEFAULT_MODEL,
        openai_api_key=ZHIPU_API_KEY,
        openai_api_base=ZHIPU_API_BASE,
        temperature=temperature,
        **kwargs
    )


# 预配置的 LLM 实例
llm = get_llm()
```

### 5.2 工具定义 (`services/langchain_tools.py`)

```python
"""
LangChain 工具定义
使用 @tool 装饰器定义日程管理工具
"""
from langchain.tools import tool
from typing import Optional
from services.schedule_service import ScheduleService


def get_tools(schedule_service: ScheduleService):
    """获取日程管理工具集"""

    @tool
    async def get_current_datetime() -> str:
        """获取当前的日期和时间（ISO格式）。处理任何涉及时间的请求前，必须先调用此函数。"""
        from datetime import datetime
        now = datetime.now()
        weekdays = ["星期一", "星期二", "星期三", "星期四", "星期五", "星期六", "星期日"]
        return f"当前时间（ISO格式）：{now.strftime('%Y-%m-%d %H:%M:%S')}\n日期：{now.strftime('%Y年%m月%d日')}\n星期：{weekdays[now.weekday()]}"

    @tool
    async def parse_time_to_iso(natural_time: str) -> str:
        """将自然语言时间转换为ISO格式。创建或修改日程前，必须先调用此函数。

        Args:
            natural_time: 用户说的自然语言时间，如：明天下午三点、后天晚上十点、周五上午9点
        """
        from utils.time_parser import parse_time
        from datetime import datetime
        parsed = parse_time(natural_time, datetime.now())
        if parsed:
            return f"时间解析结果：{parsed.strftime('%Y-%m-%d %H:%M')}"
        return f"无法解析时间：{natural_time}"

    @tool
    async def create_schedule(title: str, datetime: str, description: str = "") -> str:
        """创建新日程。⚠️ datetime 参数必须是 ISO 格式（YYYY-MM-DD HH:MM）！

        Args:
            title: 日程标题，如：开会、看病、健身
            datetime: 日程时间，必须是 ISO 格式，如 2026-02-24 15:00
            description: 日程的详细描述（可选）
        """
        schedule = await schedule_service.create_schedule(
            title=title,
            time_str=datetime,
            description=description or None
        )
        if schedule:
            return f"日程创建成功！\n{schedule_service.format_schedule(schedule)}"
        return "创建日程失败，请检查时间格式。"

    @tool
    async def query_schedules(date: str = "今天") -> str:
        """查询指定日期的日程。

        Args:
            date: 查询日期，如：今天、明天、后天、本周
        """
        schedules = await schedule_service.list_schedules(date_str=date)
        if not schedules:
            return f"{date}没有日程安排。"
        result = f"📅 {date}的日程：\n\n"
        for i, s in enumerate(schedules, 1):
            result += f"{i}. {schedule_service.format_schedule(s)}\n\n"
        return result.strip()

    @tool
    async def list_all_schedules() -> str:
        """列出用户的所有日程（带ID），用于修改或删除时获取日程ID。"""
        # 实现略
        pass

    @tool
    async def update_schedule(schedule_id: int, title: Optional[str] = None,
                              datetime: Optional[str] = None,
                              description: Optional[str] = None) -> str:
        """修改已有日程。

        Args:
            schedule_id: 要修改的日程ID
            title: 新的日程标题（可选）
            datetime: 新的日程时间，必须是 ISO 格式（可选）
            description: 新的备注内容（可选）
        """
        schedule = await schedule_service.update_schedule(
            schedule_id=schedule_id,
            title=title,
            time_str=datetime,
            description=description
        )
        if schedule:
            return f"日程修改成功！\n{schedule_service.format_schedule(schedule)}"
        return f"修改失败，未找到日程 (ID: {schedule_id})"

    @tool
    async def delete_schedule(schedule_id: int) -> str:
        """删除日程。

        Args:
            schedule_id: 要删除的日程ID
        """
        success = await schedule_service.delete_schedule(schedule_id)
        if success:
            return f"已删除日程 (ID: {schedule_id})"
        return f"删除失败，未找到日程 (ID: {schedule_id})"

    @tool
    async def find_schedule_by_keyword(keyword: str, date: Optional[str] = None) -> str:
        """通过标题关键词搜索日程。

        Args:
            keyword: 日程标题中的关键词
            date: 日期筛选（可选）：今天、明天、后天
        """
        schedules = await schedule_service.find_schedules_by_keyword(
            keyword=keyword,
            date_str=date
        )
        if not schedules:
            return f"没有找到标题包含「{keyword}」的日程。"
        result = f"找到 {len(schedules)} 个包含「{keyword}」的日程：\n\n"
        for s in schedules:
            result += f"[ID:{s.id}] {schedule_service.format_schedule(s)}\n\n"
        return result.strip()

    @tool
    async def shift_schedule_time(schedule_id: int, shift_minutes: int) -> str:
        """偏移日程时间（提前或推迟）。

        Args:
            schedule_id: 日程ID
            shift_minutes: 偏移分钟数。正数=推迟，负数=提前。如：提前30分钟=-30，推迟1小时=60
        """
        schedule = await schedule_service.shift_schedule_time(
            schedule_id=schedule_id,
            shift_minutes=shift_minutes
        )
        if schedule:
            direction = "推迟" if shift_minutes > 0 else "提前"
            abs_min = abs(shift_minutes)
            if abs_min >= 1440:
                time_desc = f"{abs_min // 1440}天"
            elif abs_min >= 60:
                time_desc = f"{abs_min // 60}小时"
            else:
                time_desc = f"{abs_min}分钟"
            return f"已{direction}{time_desc}！\n{schedule_service.format_schedule(schedule)}"
        return f"时间调整失败 (ID: {schedule_id})"

    return [
        get_current_datetime,
        parse_time_to_iso,
        create_schedule,
        query_schedules,
        list_all_schedules,
        update_schedule,
        delete_schedule,
        find_schedule_by_keyword,
        shift_schedule_time,
    ]
```

### 5.3 Agent 服务 (`services/langchain_agent.py`)

```python
"""
LangGraph Agent 服务
使用 LangGraph StateGraph 进行状态管理
"""
import os
import logging
from typing import TypedDict, Annotated
from datetime import datetime

from langchain_openai import ChatOpenAI
from langchain.agents import create_agent
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
from langgraph.graph import StateGraph, MessagesState, START, END
from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver

from config import ZHIPU_API_KEY, DATA_DIR
from services.langchain_llm import get_llm
from services.langchain_tools import get_tools
from services.schedule_service import ScheduleService

logger = logging.getLogger(__name__)

# 系统提示词
SYSTEM_PROMPT = """你是一个友好、智能的AI助手。

【核心定位】
- 你首先是一个可以回答各种问题的AI助手
- 你还具备日程管理的额外能力

【⚠️ 创建日程的正确流程】
1. 用户说要添加日程时，先调用 get_current_datetime 获取当前时间
2. 再调用 parse_time_to_iso 将用户说的时间转换为 ISO 格式
3. 使用返回的 ISO 时间调用 create_schedule

【⚠️ 多日程处理】
用户一次说多个日程时，要逐个处理，每个日程都要完整执行上述流程。

【⚠️ 修改日程的正确流程】
1. 用户不知道ID时，调用 find_schedule_by_keyword 或 list_all_schedules
2. 用户说"提前/推迟 X 分钟/小时"时，使用 shift_schedule_time
3. 用户要改具体时间时，先 parse_time_to_iso 再 update_schedule

【工具列表】
- get_current_datetime: 获取当前时间
- parse_time_to_iso: 解析自然语言时间
- create_schedule: 创建日程
- query_schedules: 查询日程
- list_all_schedules: 列出所有日程
- find_schedule_by_keyword: 搜索日程
- update_schedule: 修改日程
- shift_schedule_time: 偏移时间
- delete_schedule: 删除日程

【重要】
- 闲聊、问候、知识问答等不调用工具，直接对话
- 请用中文回复
- 回复简洁友好"""


class LangChainAgentService:
    """LangGraph Agent 服务"""

    def __init__(self):
        self.llm = get_llm(temperature=0.7)
        self._checkpointer = None

    async def _get_checkpointer(self) -> AsyncSqliteSaver:
        """获取或创建 checkpointer"""
        if self._checkpointer is None:
            db_path = os.path.join(DATA_DIR, "checkpoints.db")
            self._checkpointer = AsyncSqliteSaver.from_conn_string(db_path)
            await self._checkpointer.setup()
        return self._checkpointer

    async def process(self, message: str, user_id: str, db_session) -> str:
        """
        处理用户消息

        Args:
            message: 用户消息
            user_id: 用户 ID
            db_session: 数据库会话

        Returns:
            AI 回复
        """
        try:
            # 创建日程服务
            schedule_service = ScheduleService(db_session)

            # 获取工具
            tools = get_tools(schedule_service)

            # 创建 Agent
            agent = create_agent(
                self.llm,
                tools=tools,
                system_prompt=SYSTEM_PROMPT
            )

            # 获取 checkpointer
            checkpointer = await self._get_checkpointer()

            # 编译 graph
            graph = agent.compile(checkpointer=checkpointer)

            # 配置（使用 user_id 作为 thread_id）
            config = {"configurable": {"thread_id": user_id}}

            # 调用 Agent
            result = await graph.ainvoke(
                {"messages": [HumanMessage(content=message)]},
                config=config
            )

            # 提取回复
            return result["messages"][-1].content

        except Exception as e:
            logger.error(f"Agent 处理失败: {e}", exc_info=True)
            return f"抱歉，处理请求时出错：{str(e)}"


# 全局实例
langchain_agent = LangChainAgentService()
```

### 5.4 微信路由修改 (`app/routers/wechat.py`)

```python
# 主要修改点：将 agent_service 替换为 langchain_agent

# 原来
from services.agent_service import ScheduleAgentService
agent_service = ScheduleAgentService(zhipu_api_key=ZHIPU_API_KEY)

# 修改后
from services.langchain_agent import langchain_agent
# 直接使用 langchain_agent.process()
```

---

## 六、迁移步骤

### 阶段一：环境准备（0.5 天）

- [ ] 1.1 安装 uv
  ```bash
  # macOS/Linux
  curl -LsSf https://astral.sh/uv/install.sh | sh

  # Windows (PowerShell)
  powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
  ```

- [ ] 1.2 创建 pyproject.toml

- [ ] 1.3 使用 uv 安装依赖
  ```bash
  uv sync
  ```

- [ ] 1.4 验证开发环境
  ```bash
  uv run python main.py
  ```

### 阶段二：LangChain 基础搭建（1 天）

- [ ] 2.1 创建 `services/langchain_llm.py` - LLM 封装
- [ ] 2.2 创建 `services/langchain_tools.py` - 工具定义
- [ ] 2.3 创建 `services/langchain_agent.py` - Agent 服务
- [ ] 2.4 单元测试 - 验证工具调用正常

### 阶段三：集成迁移（1 天）

- [ ] 3.1 修改 `app/routers/wechat.py` - 调用新 Agent
- [ ] 3.2 修改 `config.py` - 添加 LangChain 配置
- [ ] 3.3 本地测试 - 验证微信消息处理
- [ ] 3.4 对话持久化测试 - 验证 SQLite checkpointer

### 阶段四：功能验证（1 天）

- [ ] 4.1 日程创建测试
- [ ] 4.2 日程查询测试
- [ ] 4.3 日程修改测试
- [ ] 4.4 日程删除测试
- [ ] 4.5 多轮对话测试（记忆功能）
- [ ] 4.6 语音消息测试

### 阶段五：部署上线（0.5 天）

- [ ] 5.1 删除旧文件 `services/agent_service.py`
- [ ] 5.2 更新服务器上的依赖
- [ ] 5.3 重启服务
- [ ] 5.4 线上验证

### 阶段六：清理与文档（0.5 天）

- [ ] 6.1 删除 `requirements.txt`
- [ ] 6.2 更新 README.md
- [ ] 6.3 更新部署文档
- [ ] 6.4 代码审查与优化

---

## 七、回滚方案

如果重构出现问题，按以下步骤回滚：

1. **恢复旧代码**
   ```bash
   git checkout HEAD~1 -- services/agent_service.py
   git checkout HEAD~1 -- app/routers/wechat.py
   ```

2. **恢复依赖**
   ```bash
   # 恢复 requirements.txt
   git checkout HEAD~1 -- requirements.txt
   pip install -r requirements.txt
   ```

3. **重启服务**
   ```bash
   # 在服务器上
   pkill -f "python main.py"
   cd /opt/wxzhushou && source venv/bin/activate && nohup python main.py > app.log 2>&1 &
   ```

---

## 八、测试用例

### 8.1 基础对话测试

| 输入 | 期望输出 |
|-----|---------|
| 你好 | 友好的问候回复 |
| 现在几点 | 返回当前时间 |
| 今天星期几 | 返回星期几 |

### 8.2 日程管理测试

| 输入 | 期望行为 |
|-----|---------|
| 明天下午3点开会 | 创建日程，时间解析正确 |
| 后天上午10点去医院，带医保卡 | 创建带描述的日程 |
| 22号回家，24号打针 | 创建2个日程 |
| 明天有什么安排 | 查询并返回日程列表 |
| 把开会那个日程改到后天 | 搜索并修改日程 |
| 提前30分钟 | 使用 shift_schedule_time |
| 删除日程1 | 删除指定日程 |

### 8.3 多轮对话测试

| 轮次 | 输入 | 期望 |
|-----|------|------|
| 1 | 帮我记一下 | 追问记什么 |
| 2 | 明天下午开会 | 追问具体时间 |
| 3 | 3点 | 创建日程 |

### 8.4 边界测试

| 场景 | 输入 | 期望 |
|-----|------|------|
| 无效时间 | 32号开会 | 提示时间无效 |
| 空日程 | 查看昨天的日程 | 返回空列表 |
| 错误ID | 删除日程999 | 提示不存在 |

---

## 九、风险评估

| 风险 | 概率 | 影响 | 缓解措施 |
|-----|------|------|---------|
| LangChain API 变化 | 中 | 中 | 使用稳定版本 1.2.x |
| 智谱 API 不兼容 | 低 | 高 | 已验证 ChatOpenAI 兼容 |
| 功能回归 | 中 | 高 | 完整测试用例 |
| 性能下降 | 低 | 中 | 异步优化 |
| 依赖冲突 | 低 | 中 | uv 环境隔离 |

---

## 十、参考资料

- [LangChain 官方文档](https://python.langchain.com/)
- [LangGraph 文档](https://langchain-ai.github.io/langgraph/)
- [uv 官方文档](https://docs.astral.sh/uv/)
- [智谱 AI API 文档](https://open.bigmodel.cn/dev/api)

---

## 十一、变更记录

| 日期 | 版本 | 变更内容 | 作者 |
|-----|------|---------|------|
| 2026-02-24 | v1.0 | 初始版本 | - |

---

**确认签字**：________________  **日期**：________________
