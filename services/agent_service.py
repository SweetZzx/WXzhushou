"""
LangChain Agent 服务
整合 GLM 和工具调用 - 使用 LangChain 1.0 API
"""
from langchain.agents import create_agent
from langchain_openai import ChatOpenAI
from typing import List
import logging

from services.langchain_tools import create_schedule_tools
from services.schedule_service import ScheduleService

logger = logging.getLogger(__name__)


class ScheduleAgentService:
    """日程助手 Agent 服务"""

    # 系统提示词
    SYSTEM_PROMPT = """你是一个智能日程助手，可以帮助用户管理日程。

你的功能包括：
1. 创建日程 - 记录用户安排的时间和事件
2. 查询日程 - 帮用户查看特定日期的安排
3. 修改日程 - 更新已存在的日程信息
4. 删除日程 - 移除不需要的日程

使用指南：
- 创建日程时，尽量获取完整信息（标题、时间、描述）
- 查询时，默认查询"今天"的日程
- 修改和删除前，确认日程ID是否正确
- 使用友好、简洁的语言与用户交流
- 操作成功后，简要确认结果

请用中文回复。"""

    def __init__(self, zhipu_api_key: str, model: str = "glm-4"):
        """
        初始化 Agent 服务

        Args:
            zhipu_api_key: 智谱AI API密钥
            model: 模型名称
        """
        self.api_key = zhipu_api_key
        self.model = model

        # 初始化 LLM（使用 OpenAI 兼容接口）
        # 智谱AI支持 OpenAI 兼容的 API 格式
        self.llm = ChatOpenAI(
            api_key=zhipu_api_key,
            base_url="https://open.bigmodel.cn/api/paas/v4/",
            model=model,
            temperature=0.7,
        )

        logger.info("ScheduleAgentService 初始化成功")

    async def process(
        self,
        message: str,
        user_id: str,
        db_session
    ) -> str:
        """
        处理用户消息

        Args:
            message: 用户消息
            user_id: 用户ID
            db_session: 数据库会话

        Returns:
            Agent 的回复
        """
        try:
            # 创建日程服务实例
            schedule_service = ScheduleService(db_session)

            # 创建工具集
            tools = create_schedule_tools(schedule_service, user_id)

            # 使用新的 create_agent API (LangChain 1.0)
            agent = create_agent(
                self.llm,
                tools=tools,
                system_prompt=self.SYSTEM_PROMPT
            )

            # 执行 Agent
            result = agent.invoke({
                "messages": [{"role": "user", "content": message}]
            })

            # 提取最后一条消息的内容
            last_message = result["messages"][-1]
            if hasattr(last_message, "content"):
                return last_message.content
            else:
                return str(last_message)

        except Exception as e:
            logger.error(f"Agent 处理失败: {e}", exc_info=True)
            return f"抱歉，处理请求时出错：{str(e)}"

    async def chat(self, message: str, user_id: str) -> str:
        """
        普通对话（不使用 Agent）

        Args:
            message: 用户消息
            user_id: 用户ID

        Returns:
            AI 回复
        """
        try:
            from langchain_core.messages import HumanMessage

            messages = [HumanMessage(content=message)]
            response = await self.llm.ainvoke(messages)

            return response.content

        except Exception as e:
            logger.error(f"对话失败: {e}", exc_info=True)
            return f"抱歉，AI 回复出错：{str(e)}"


# 便捷函数
async def process_schedule_request(
    message: str,
    user_id: str,
    db_session,
    api_key: str
) -> str:
    """
    处理日程请求（便捷函数）

    Args:
        message: 用户消息
        user_id: 用户ID
        db_session: 数据库会话
        api_key: 智谱AI API密钥

    Returns:
        Agent 回复
    """
    agent = ScheduleAgentService(api_key)
    return await agent.process(message, user_id, db_session)
