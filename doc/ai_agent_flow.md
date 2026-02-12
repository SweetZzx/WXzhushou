# AI Agent 对话流程技术文档（新手版）

## 一、什么是 AI Agent？

### 简单理解

想象你在餐厅点餐：
- **普通AI对话**：就像服务员只是听你说话，然后回答你
- **AI Agent**：就像服务员不仅能和你聊天，还能**帮你做事**（下单、查菜单、退菜等）

我们的项目就是一个 **AI Agent**，它不仅能和你聊天，还能：
- 📅 帮你创建日程
- 🔍 帮你查询日程
- ✏️ 帮你修改日程
- 🗑️ 帮你删除日程

### 核心概念对比

| 概念 | 类比 | 说明 |
|-----|------|------|
| **System Prompt** | 员工手册 | 告诉AI它是什么角色，应该怎么工作 |
| **Tools/Functions** | 工具箱 | AI可以调用的功能（创建日程、查询等） |
| **Function Calling** | 使用工具 | AI判断需要使用哪个工具并执行 |
| **Context/Memory** | 工作记忆 | 记住对话的上下文 |

---

## 二、整体流程图（从发消息到收到回复）

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              用户在微信发送消息                                │
│                           "明天下午3点开会"                                   │
└─────────────────────────────────────────────────────────────────────────────┘
                                      │
                                      ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│  第1步：微信服务器接收消息                                                    │
│  ─────────────────────────────                                               │
│  微信服务器把消息封装成XML格式，发送到我们的服务器                              │
└─────────────────────────────────────────────────────────────────────────────┘
                                      │
                                      ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│  第2步：我们的服务器接收请求                                                  │
│  ─────────────────────────────                                               │
│  文件：app/routers/wechat.py                                                 │
│  - 验证请求来自微信服务器                                                     │
│  - 解析XML，提取：发送者ID、消息内容、消息类型                                 │
└─────────────────────────────────────────────────────────────────────────────┘
                                      │
                                      ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│  第3步：调用 AI Agent 服务                                                   │
│  ─────────────────────────────                                               │
│  文件：services/agent_service.py                                             │
│  - 创建 ScheduleService 实例（用于操作数据库）                                │
│  - 准备系统提示词（System Prompt）                                           │
│  - 准备工具定义（Tools Definition）                                          │
└─────────────────────────────────────────────────────────────────────────────┘
                                      │
                                      ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│  第4步：调用智谱AI API                                                       │
│  ─────────────────────────────                                               │
│  发送给AI的内容：                                                             │
│  ┌─────────────────────────────────────────────────────────────────────┐    │
│  │ System: 你是一个友好、智能的AI助手...（系统提示词）                    │    │
│  │ User: 明天下午3点开会                                                 │    │
│  │ Tools: [create_schedule, query_schedules, ...]（可用工具列表）        │    │
│  └─────────────────────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────────────────────┘
                                      │
                                      ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│  第5步：AI分析并决定调用工具                                                  │
│  ─────────────────────────────                                               │
│  AI的思考过程：                                                               │
│  "用户说明天下午3点开会，这是要创建日程"                                       │
│  "我应该调用 create_schedule 工具"                                           │
│  "参数是：title='开会', datetime='明天下午3点'"                               │
│                                                                              │
│  AI返回：                                                                     │
│  ┌─────────────────────────────────────────────────────────────────────┐    │
│  │ tool_calls: [                                                        │    │
│  │   {                                                                  │    │
│  │     "name": "create_schedule",                                       │    │
│  │     "arguments": "{\"title\": \"开会\", \"datetime\": \"明天下午3点\"}"│   │
│  │   }                                                                  │    │
│  │ ]                                                                    │    │
│  └─────────────────────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────────────────────┘
                                      │
                                      ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│  第6步：执行工具函数                                                          │
│  ─────────────────────────────                                               │
│  agent_service.py 中的 _execute_tool 方法：                                  │
│                                                                              │
│  1. 解析工具名称和参数                                                        │
│     tool_name = "create_schedule"                                           │
│     tool_args = {"title": "开会", "datetime": "明天下午3点"}                 │
│                                                                              │
│  2. 调用 schedule_service.create_schedule()                                 │
│     - 解析时间："明天下午3点" → 2026-02-13 15:00:00                          │
│     - 写入数据库：INSERT INTO schedules (...)                                │
│                                                                              │
│  3. 返回执行结果                                                              │
│     "日程创建成功！\n📅 开会\n⏰ 明天 15:00"                                  │
└─────────────────────────────────────────────────────────────────────────────┘
                                      │
                                      ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│  第7步：把工具执行结果发回AI                                                  │
│  ─────────────────────────────                                               │
│  再次调用智谱AI API，这次包含工具执行结果：                                    │
│  ┌─────────────────────────────────────────────────────────────────────┐    │
│  │ System: 你是一个友好、智能的AI助手...                                 │    │
│  │ User: 明天下午3点开会                                                 │    │
│  │ Assistant: [调用工具 create_schedule]                                 │    │
│  │ Tool Result: "日程创建成功！\n📅 开会\n⏰ 明天 15:00"                  │    │
│  └─────────────────────────────────────────────────────────────────────┘    │
│                                                                              │
│  AI生成最终回复：                                                             │
│  "好的，已经帮您创建日程了！明天15:00 开会，记得准时参加哦~"                   │
└─────────────────────────────────────────────────────────────────────────────┘
                                      │
                                      ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│  第8步：封装回复返回给微信                                                    │
│  ─────────────────────────────                                               │
│  wechat.py 把AI回复封装成XML格式：                                            │
│  ┌─────────────────────────────────────────────────────────────────────┐    │
│  │ <xml>                                                                │    │
│  │   <ToUserName><![CDATA[用户OpenID]]></ToUserName>                    │    │
│  │   <FromUserName><![CDATA[公众号ID]]></FromUserName>                  │    │
│  │   <CreateTime>1707753600</CreateTime>                                │    │
│  │   <MsgType><![CDATA[text]]></MsgType>                                │    │
│  │   <Content><![CDATA[好的，已经帮您创建日程了！...]]></Content>         │    │
│  │ </xml>                                                               │    │
│  └─────────────────────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────────────────────┘
                                      │
                                      ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│  第9步：微信服务器转发给用户                                                  │
│  ─────────────────────────────                                               │
│  用户在微信中看到回复：                                                        │
│  "好的，已经帮您创建日程了！明天15:00 开会，记得准时参加哦~"                   │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 三、详细代码解析

### 3.1 入口：微信消息接收 (wechat.py)

```python
# 文件：app/routers/wechat.py

@router.post("")
async def wechat_message(request: Request, db = Depends(get_db)):
    """微信消息接收接口"""

    # 步骤1：获取原始请求数据
    body = await request.body()
    body_str = body.decode("utf-8")
    # body_str 的内容类似：
    # <xml>
    #   <FromUserName>oKXgA2f3rTVyibzgiX-PEfmXxmUc</FromUserName>
    #   <Content>明天下午3点开会</Content>
    #   ...
    # </xml>

    # 步骤2：解析XML消息
    message = wechat_service.parse_message(body_str)
    # 解析后得到字典：
    # {
    #     "FromUserName": "oKXgA2f3rTVyibzgiX-PEfmXxmUc",
    #     "Content": "明天下午3点开会",
    #     "MsgType": "text",
    #     ...
    # }

    # 步骤3：提取关键信息
    from_user = message.get("FromUserName", "")  # 用户OpenID
    content = message.get("Content", "")          # 消息内容

    # 步骤4：调用AI Agent处理消息
    ai_response = await agent_service.process(content, from_user, db)

    # 步骤5：返回XML格式响应
    xml_response = wechat_service.create_response_xml(ai_response, from_user, to_user)
    return Response(content=xml_response, media_type="application/xml")
```

### 3.2 核心：AI Agent 服务 (agent_service.py)

```python
# 文件：services/agent_service.py

class ScheduleAgentService:
    """AI 助手服务"""

    # 系统提示词 - 告诉AI它的角色和能力
    SYSTEM_PROMPT = """你是一个友好、智能的AI助手。

【核心定位】
- 你首先是一个可以回答各种问题的AI助手
- 你还具备日程管理的额外能力

【工具使用规则】
1. 查看时间/日期：使用 get_current_time 或 get_date_info
2. 创建日程：用户想记录、安排、计划某事时使用 create_schedule
3. 查询日程：用户想查看日程时使用 query_schedules
4. 列出所有日程：使用 list_all_schedules
5. 修改日程：使用 update_schedule
6. 删除日程：使用 delete_schedule
7. 提醒设置：使用 get_reminder_settings 或 update_reminder_settings

【重要】
- 闲聊、问候、知识问答等不调用工具，直接对话
- 请用中文回复
- 回复简洁友好"""

    def __init__(self, zhipu_api_key: str, model: str = "glm-4"):
        """初始化 - 创建智谱AI客户端"""
        self.client = ZhipuAI(api_key=zhipu_api_key)

    def _build_tools(self) -> list:
        """构建工具定义 - 告诉AI有哪些工具可用"""
        return [
            {
                "type": "function",
                "function": {
                    "name": "create_schedule",           # 工具名称
                    "description": "创建新日程。当用户想要记录、安排、计划某事时使用。",
                    "parameters": {                       # 参数定义
                        "type": "object",
                        "properties": {
                            "title": {
                                "type": "string",
                                "description": "日程标题，如：开会、看病、健身"
                            },
                            "datetime": {
                                "type": "string",
                                "description": "日程时间，如：明天下午3点"
                            },
                            "description": {
                                "type": "string",
                                "description": "日程的详细描述（可选）"
                            }
                        },
                        "required": ["title", "datetime"]  # 必填参数
                    }
                }
            },
            # ... 其他工具定义（query_schedules, delete_schedule 等）
        ]

    async def process(self, message: str, user_id: str, db_session) -> str:
        """
        处理用户消息 - 核心流程

        这是整个AI Agent的核心方法，实现了"思考-行动"循环
        """
        # 步骤1：准备服务实例
        schedule_service = ScheduleService(db_session)
        tools = self._build_tools()

        # 步骤2：构建消息列表
        messages = [
            {"role": "system", "content": self.SYSTEM_PROMPT},  # 系统提示
            {"role": "user", "content": message}                 # 用户消息
        ]

        # 步骤3：思考-行动循环（最多5次迭代）
        max_iterations = 5
        for iteration in range(max_iterations):

            # 3.1 调用AI API
            response = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                tools=tools,              # 传入可用工具
                tool_choice="auto",       # 让AI自己决定是否调用工具
                temperature=0.7           # 创造性参数
            )

            assistant_message = response.choices[0].message

            # 3.2 检查AI是否要调用工具
            if not assistant_message.tool_calls:
                # AI不需要调用工具，直接返回回复
                return assistant_message.content

            # 3.3 AI要调用工具，先记录AI的消息
            messages.append({
                "role": "assistant",
                "content": assistant_message.content or "",
                "tool_calls": [
                    {
                        "id": tc.id,
                        "type": "function",
                        "function": {
                            "name": tc.function.name,
                            "arguments": tc.function.arguments
                        }
                    }
                    for tc in assistant_message.tool_calls
                ]
            })

            # 3.4 执行每个工具调用
            for tool_call in assistant_message.tool_calls:
                function_name = tool_call.function.name
                function_args = json.loads(tool_call.function.arguments)

                # 执行工具函数
                result = await self._execute_tool(
                    function_name,
                    function_args,
                    schedule_service,
                    user_id
                )

                # 把工具执行结果加入消息列表
                messages.append({
                    "role": "tool",
                    "tool_call_id": tool_call.id,
                    "content": result
                })

            # 3.5 继续循环，让AI根据工具结果生成最终回复

        return "抱歉，处理您的请求时超出了最大迭代次数。"

    async def _execute_tool(self, tool_name: str, tool_args: dict,
                           schedule_service: ScheduleService, user_id: str) -> str:
        """
        执行工具函数

        根据工具名称，调用相应的功能
        """
        if tool_name == "create_schedule":
            # 创建日程
            title = tool_args.get("title", "")
            datetime_str = tool_args.get("datetime", "")
            description = tool_args.get("description", "")

            schedule = await schedule_service.create_schedule(
                user_id=user_id,
                title=title,
                time_str=datetime_str,
                description=description or None
            )

            if schedule:
                return f"日程创建成功！\n{schedule_service.format_schedule(schedule)}"
            return "创建日程失败，请检查时间格式是否正确。"

        elif tool_name == "query_schedules":
            # 查询日程
            date = tool_args.get("date", "今天")
            schedules = await schedule_service.list_schedules(user_id=user_id, date_str=date)

            if not schedules:
                return f"{date}没有日程安排。"

            result = f"📅 {date}的日程：\n\n"
            for i, schedule in enumerate(schedules, 1):
                result += f"{i}. {schedule_service.format_schedule(schedule)}\n\n"
            return result.strip()

        # ... 其他工具的处理逻辑

        return f"未知工具: {tool_name}"
```

### 3.3 工具执行：日程服务 (schedule_service.py)

```python
# 文件：services/schedule_service.py

class ScheduleService:
    """日程服务 - 负责数据库操作"""

    async def create_schedule(self, user_id: str, title: str, time_str: str,
                              description: str = None) -> Optional[Schedule]:
        """
        创建日程

        步骤：
        1. 解析时间字符串（如"明天下午3点"）
        2. 验证时间不能是过去
        3. 写入数据库
        """
        # 步骤1：解析时间
        scheduled_time = parse_time(time_str)  # "明天下午3点" → datetime对象
        if not scheduled_time:
            logger.error(f"无法解析时间: {time_str}")
            return None

        # 步骤2：验证时间
        if scheduled_time < datetime.now():
            logger.warning(f"日程时间不能是过去: {scheduled_time}")
            return None

        # 步骤3：创建数据库记录
        schedule = Schedule(
            user_id=user_id,
            title=title,
            description=description,
            scheduled_time=scheduled_time,
            status="active"
        )

        self.db.add(schedule)
        await self.db.commit()
        await self.db.refresh(schedule)

        return schedule
```

---

## 四、关键概念详解

### 4.1 System Prompt（系统提示词）

**是什么？**
就像给新员工发的"员工手册"，告诉AI：
- 它是什么角色
- 它能做什么
- 它应该怎么回答

**示例**：
```
你是一个友好、智能的AI助手。

【核心定位】
- 你首先是一个可以回答各种问题的AI助手
- 你还具备日程管理的额外能力

【工具使用规则】
1. 创建日程：用户想记录、安排、计划某事时使用 create_schedule
...
```

### 4.2 Tools/Functions（工具定义）

**是什么？**
告诉AI有哪些"工具"可以使用，每个工具需要什么参数。

**格式示例**：
```python
{
    "type": "function",
    "function": {
        "name": "create_schedule",           # 工具名称
        "description": "创建新日程",          # 工具描述（AI根据这个判断何时使用）
        "parameters": {
            "type": "object",
            "properties": {
                "title": {"type": "string", "description": "日程标题"},
                "datetime": {"type": "string", "description": "日程时间"}
            },
            "required": ["title", "datetime"]
        }
    }
}
```

### 4.3 Function Calling（函数调用）

**是什么？**
AI分析用户消息后，决定要调用哪个工具，并提取参数。

**流程**：
```
用户输入："明天下午3点开会"
    ↓
AI分析：用户要创建日程
    ↓
AI决定：调用 create_schedule 工具
    ↓
AI提取参数：title="开会", datetime="明天下午3点"
    ↓
返回工具调用请求
```

### 4.4 思考-行动循环（ReAct Pattern）

**是什么？**
AI Agent的核心工作模式：思考 → 行动 → 观察 → 再思考

```
┌──────────────────────────────────────────────────────┐
│                    思考-行动循环                       │
├──────────────────────────────────────────────────────┤
│                                                      │
│    ┌─────────┐      ┌─────────┐      ┌─────────┐   │
│    │  思考   │─────▶│  行动   │─────▶│  观察   │   │
│    │ (Think) │      │  (Act)  │      │(Observe)│   │
│    └─────────┘      └─────────┘      └─────────┘   │
│         ▲                                   │        │
│         └───────────────────────────────────┘        │
│                   (循环)                             │
│                                                      │
│  思考：AI分析用户消息，决定是否需要调用工具           │
│  行动：执行工具函数                                   │
│  观察：获取工具执行结果                               │
│  循环：如果需要，继续思考下一步                       │
│                                                      │
└──────────────────────────────────────────────────────┘
```

---

## 五、消息流转详解

### 5.1 消息列表（Messages）的结构

在整个对话过程中，我们维护一个消息列表：

```python
messages = [
    # 1. 系统消息
    {"role": "system", "content": "你是一个友好、智能的AI助手..."},

    # 2. 用户消息
    {"role": "user", "content": "明天下午3点开会"},

    # 3. AI的回复（包含工具调用）
    {
        "role": "assistant",
        "content": "",
        "tool_calls": [{
            "id": "call_123",
            "type": "function",
            "function": {
                "name": "create_schedule",
                "arguments": '{"title": "开会", "datetime": "明天下午3点"}'
            }
        }]
    },

    # 4. 工具执行结果
    {
        "role": "tool",
        "tool_call_id": "call_123",
        "content": "日程创建成功！\n📅 开会\n⏰ 明天 15:00"
    },

    # 5. AI的最终回复（不带工具调用）
    {"role": "assistant", "content": "好的，已经帮您创建日程了！..."}
]
```

### 5.2 完整的消息时序图

```
时间线 →

用户          wechat.py      agent_service.py      智谱AI API       数据库
  │               │                  │                 │              │
  │  "明天下午3点开会"                │                 │              │
  │──────────────▶│                  │                 │              │
  │               │                  │                 │              │
  │               │ process(msg,uid) │                 │              │
  │               │─────────────────▶│                 │              │
  │               │                  │                 │              │
  │               │                  │ chat.completions│              │
  │               │                  │ create()        │              │
  │               │                  │────────────────▶│              │
  │               │                  │                 │              │
  │               │                  │ tool_calls:     │              │
  │               │                  │ create_schedule │              │
  │               │                  │◀────────────────│              │
  │               │                  │                 │              │
  │               │                  │ _execute_tool() │              │
  │               │                  │─────────────────────────────▶ │
  │               │                  │                 │   INSERT     │
  │               │                  │                 │              │
  │               │                  │ "日程创建成功"  │              │
  │               │                  │◀───────────────────────────── │
  │               │                  │                 │              │
  │               │                  │ 再次调用API     │              │
  │               │                  │ (带工具结果)    │              │
  │               │                  │────────────────▶│              │
  │               │                  │                 │              │
  │               │                  │ 最终回复        │              │
  │               │                  │◀────────────────│              │
  │               │                  │                 │              │
  │               │ "好的，已经帮您..."                 │              │
  │               │◀─────────────────│                 │              │
  │               │                  │                 │              │
  │ "好的，已经帮您..."               │                 │              │
  │◀──────────────│                  │                 │              │
  │               │                  │                 │              │
```

---

## 六、常见场景流程

### 场景1：创建日程

```
用户输入："明天下午3点开会"

步骤1：AI分析
  - 识别意图：创建日程
  - 提取信息：title="开会", datetime="明天下午3点"

步骤2：调用工具
  - 工具：create_schedule
  - 参数：{title: "开会", datetime: "明天下午3点"}

步骤3：执行工具
  - 解析时间：明天下午3点 → 2026-02-13 15:00:00
  - 写入数据库
  - 返回结果："日程创建成功！..."

步骤4：AI生成回复
  - 输入：工具执行结果
  - 输出："好的，已经帮您创建日程了！明天15:00 开会..."

步骤5：返回用户
```

### 场景2：查询日程

```
用户输入："明天有什么安排"

步骤1：AI分析
  - 识别意图：查询日程
  - 提取信息：date="明天"

步骤2：调用工具
  - 工具：query_schedules
  - 参数：{date: "明天"}

步骤3：执行工具
  - 计算日期范围：明天 00:00 - 23:59
  - 查询数据库：SELECT * FROM schedules WHERE ...
  - 返回结果："📅 明天的日程：\n\n1. 15:00 开会"

步骤4：AI生成回复
  - 直接使用工具结果（或稍作润色）

步骤5：返回用户
```

### 场景3：普通聊天

```
用户输入："你好"

步骤1：AI分析
  - 识别意图：打招呼（不需要调用工具）

步骤2：AI直接回复
  - 不调用任何工具
  - 直接生成回复："你好！有什么可以帮你的吗？"

步骤3：返回用户
```

---

## 七、与传统程序的对比

### 传统程序 vs AI Agent

| 特性 | 传统程序 | AI Agent |
|-----|---------|---------|
| 输入处理 | 需要精确匹配关键词 | 理解自然语言 |
| 功能选择 | 用 if-else 判断 | AI自主决策 |
| 参数提取 | 正则表达式/规则 | AI自动识别 |
| 错误处理 | 预定义错误消息 | AI友好解释 |
| 扩展性 | 需要修改代码 | 只需添加工具定义 |

### 示例对比

**用户输入**："帮我记一下后天要去医院复查"

**传统程序**：
```python
if "记" in message or "添加" in message:
    # 需要复杂的正则表达式提取信息
    match = re.search(r'(\d+)月(\d+).*?(\d+)点.*?(去医院|开会|...)', message)
    # 容易出错，难以覆盖所有情况
```

**AI Agent**：
```python
# AI自动理解并调用工具
tool_calls = [
    {
        "name": "create_schedule",
        "arguments": {
            "title": "去医院复查",
            "datetime": "后天"
        }
    }
]
# 灵活，能处理各种表达方式
```

---

## 八、技术栈说明

### 使用的核心技术

| 技术 | 用途 | 说明 |
|-----|------|------|
| **FastAPI** | Web框架 | 接收微信请求，返回响应 |
| **智谱AI SDK (zhipuai)** | AI模型调用 | 调用GLM-4模型 |
| **SQLAlchemy** | 数据库ORM | 异步操作SQLite数据库 |
| **APScheduler** | 定时任务 | 实现提醒功能 |
| **httpx** | HTTP客户端 | 调用微信API推送消息 |

### 项目依赖

```txt
# requirements.txt 相关部分

# Web框架
fastapi==0.104.1
uvicorn[standard]==0.24.0

# 智谱AI官方SDK
zhipuai

# 数据库
sqlalchemy==2.0.23
aiosqlite==0.19.0

# 定时任务
apscheduler==3.10.4

# HTTP客户端
httpx==0.25.1

# 时间解析
dateparser==1.2.0
```

---

## 九、常见问题

### Q1: AI 怎么知道什么时候调用工具？

**答**：通过工具的 `description` 字段。AI会根据描述判断用户意图是否匹配。

```python
{
    "name": "create_schedule",
    "description": "创建新日程。当用户想要记录、安排、计划某事时使用。"
    # 这里的描述告诉AI：用户说"帮我记一下"、"安排一下"时调用这个工具
}
```

### Q2: 如果AI调用了错误的工具怎么办？

**答**：有几个机制防止这种情况：

1. **精确的工具描述**：让AI清楚知道每个工具的用途
2. **参数验证**：在 `_execute_tool` 中验证参数
3. **错误处理**：工具执行失败时返回友好提示
4. **系统提示词**：在 SYSTEM_PROMPT 中明确规则

### Q3: 为什么有时候AI不调用工具？

**答**：这可能是正确的行为：

- 用户只是打招呼（"你好"）
- 用户在问一般性问题（"今天天气怎么样"）
- 用户消息不明确

如果应该调用工具但没有调用，可能是：
- 工具描述不够清晰
- 系统提示词需要优化
- 用户表达方式超出AI理解范围

### Q4: 如何添加新的工具？

**步骤**：

1. 在 `_build_tools()` 中添加工具定义：
```python
{
    "type": "function",
    "function": {
        "name": "new_function",
        "description": "新功能的描述",
        "parameters": {...}
    }
}
```

2. 在 `_execute_tool()` 中添加处理逻辑：
```python
elif tool_name == "new_function":
    # 执行新功能
    return "执行结果"
```

3. 更新 SYSTEM_PROMPT，添加工具使用规则

---

## 十、总结

### 核心要点

1. **AI Agent = AI + 工具**
   - AI负责理解和决策
   - 工具负责实际操作

2. **思考-行动循环**
   - AI分析 → 决定是否调用工具 → 执行工具 → 根据结果再思考

3. **消息列表是关键**
   - 完整记录对话历史
   - 包含系统提示、用户消息、工具调用、工具结果

4. **灵活性与可控性平衡**
   - AI能理解各种表达方式
   - 通过工具定义控制AI能做什么

### 学习路径

```
入门 → 理解基本概念（System Prompt, Tools）
      ↓
进阶 → 掌握 Function Calling 机制
      ↓
实践 → 添加新工具，优化提示词
      ↓
精通 → 调试复杂场景，优化性能
```

---

*文档版本：1.0*
*最后更新：2026-02-12*
*作者：Claude AI Assistant*
