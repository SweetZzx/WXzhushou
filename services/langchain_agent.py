"""
LangGraph Agent 服务
使用 LangGraph StateGraph 进行状态管理，支持对话持久化
"""
import os
import logging
from typing import Optional
from datetime import datetime

from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain.agents import create_agent

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

【⚠️ 创建日程的正确流程 - 必须严格遵守】
1. 用户说要添加日程时，先调用 get_current_datetime 获取当前时间
2. 再调用 parse_time_to_iso 将用户说的时间转换为 ISO 格式
3. 使用返回的 ISO 时间调用 create_schedule

【⚠️ 多日程处理】
用户一次说多个日程时，要逐个处理，每个日程都要：
1. 先调用 parse_time_to_iso 解析该日程的时间
2. 等待返回结果
3. 再调用 create_schedule 创建该日程
4. 然后处理下一个日程

示例：
用户：22号回家，24号打针
处理流程：
1. parse_time_to_iso(natural_time="22号") → 得到日期
2. create_schedule(title="回家", datetime_str=返回的日期)
3. parse_time_to_iso(natural_time="24号") → 得到日期
4. create_schedule(title="打针", datetime_str=返回的日期)
5. 回复用户：已为您添加2个日程

【⚠️ 时间解析规则】
- "22号" = 本月22号
- "下周三" = 下一个周三
- 如果没有指定时间，默认为当天 09:00
- parse_time_to_iso 会返回完整的 YYYY-MM-DD HH:MM 格式

【⚠️ 修改日程的正确流程】
1. 用户说修改日程但不知道ID时：
   - 如果用户提到标题关键词，调用 find_schedule_by_keyword 搜索
   - 如果用户只说"我的日程"或没明确指向，调用 list_all_schedules 显示列表

2. 用户说"提前/推迟 X 分钟/小时/天"时：
   - 使用 shift_schedule_time 工具，计算偏移分钟数
   - 提前30分钟 = shift_minutes=-30，推迟1小时 = shift_minutes=60，推迟1天 = shift_minutes=1440

3. 用户要改具体时间时：
   - 先调用 parse_time_to_iso 解析新时间
   - 再调用 update_schedule

【工具列表】
日程管理：
- get_current_datetime: 获取当前时间（ISO格式）
- get_current_time: 获取当前时间（友好格式）
- parse_time_to_iso: 解析自然语言时间 → 返回 YYYY-MM-DD HH:MM
- get_date_info: 获取日期详细信息
- create_schedule: 创建日程（datetime_str 必须是 ISO 格式）
- query_schedules: 查询日程（date 用 今天/明天/后天）
- list_all_schedules: 列出所有日程
- find_schedule_by_keyword: 通过标题关键词搜索日程
- update_schedule: 修改日程（标题/时间/备注）
- shift_schedule_time: 偏移日程时间（提前/推迟）
- delete_schedule: 删除日程

提醒设置：
- get_reminder_settings: 获取提醒设置
- update_reminder_settings: 修改提醒设置

【⚠️ 禁止事项】
- 禁止直接将自然语言传给 create_schedule/update_schedule 的 datetime_str 参数
- 禁止自己猜测日期，必须调用 parse_time_to_iso 获取准确时间
- 禁止说"无法处理多个日程"，必须逐个处理

【重要】
- 闲聊、问候、知识问答等不调用工具，直接对话
- 请用中文回复
- 回复简洁友好"""


class LangChainAgentService:
    """LangGraph Agent 服务"""

    def __init__(self):
        self.llm = get_llm(temperature=0.7)
        self._graph = None
        self._checkpointer = None

    async def _get_checkpointer(self):
        """获取或创建 SQLite checkpointer"""
        if self._checkpointer is None:
            try:
                from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver

                db_path = os.path.join(DATA_DIR, "checkpoints.db")
                logger.info(f"初始化 SQLite checkpointer: {db_path}")
                self._checkpointer = AsyncSqliteSaver.from_conn_string(db_path)
                await self._checkpointer.setup()
                logger.info("SQLite checkpointer 初始化成功")
            except Exception as e:
                logger.error(f"初始化 checkpointer 失败: {e}", exc_info=True)
                # 回退到内存模式
                from langgraph.checkpoint.memory import InMemorySaver
                self._checkpointer = InMemorySaver()
                logger.warning("使用内存 checkpointer（对话历史不会持久化）")
        return self._checkpointer

    async def process(self, message: str, user_id: str, db_session) -> str:
        """
        处理用户消息

        Args:
            message: 用户消息
            user_id: 用户 ID（用于对话历史隔离）
            db_session: 数据库会话

        Returns:
            AI 回复
        """
        try:
            # 创建日程服务
            schedule_service = ScheduleService(db_session)

            # 获取工具
            tools = get_tools(schedule_service, user_id)

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

            logger.info(f"处理消息: user_id={user_id}, message={message[:50]}...")

            # 调用 Agent
            result = await graph.ainvoke(
                {"messages": [HumanMessage(content=message)]},
                config=config
            )

            # 提取回复
            response = result["messages"][-1].content
            logger.info(f"Agent 回复成功: {response[:100]}...")

            return response

        except Exception as e:
            logger.error(f"Agent 处理失败: {e}", exc_info=True)
            return f"抱歉，处理请求时出错：{str(e)}"

    async def chat(self, message: str, user_id: str = "default") -> str:
        """
        普通对话（不涉及日程管理）

        Args:
            message: 用户消息
            user_id: 用户 ID

        Returns:
            AI 回复
        """
        try:
            response = await self.llm.ainvoke([
                SystemMessage(content="你是一个友好的AI助手，请用中文回复。"),
                HumanMessage(content=message)
            ])
            return response.content
        except Exception as e:
            logger.error(f"对话失败: {e}", exc_info=True)
            return f"抱歉，AI 回复出错：{str(e)}"

    def clear_history(self, user_id: str):
        """清除用户的对话历史"""
        # 对于 SQLite checkpointer，需要手动删除
        # 暂时用空的 thread_id 替代
        logger.info(f"清除用户对话历史: {user_id}")
        # TODO: 实现 checkpointer 的历史清理


# 全局实例
langchain_agent = LangChainAgentService()
