"""
LangChain Agent 服务
整合 GLM 和工具调用 - 使用 LangChain 官方 ZhipuAI 集成
"""
from langchain.agents import create_agent
from langchain_community.chat_models import ChatZhipuAI
from typing import List
import logging

from services.langchain_tools import create_schedule_tools
from services.schedule_service import ScheduleService
from services.common_tools import get_common_tools

logger = logging.getLogger(__name__)


class ScheduleAgentService:
    """AI 助手服务 - 支持日常对话和日程管理"""

    # 系统提示词
    SYSTEM_PROMPT = """你是一个友好、智能的AI助手。

【核心定位】
- 你首先是一个可以回答各种问题的AI助手
- 你还具备日程管理的额外能力，但只有在用户明确需要时才使用

【日程工具使用规则】
只有当用户明确表达以下意图时，才调用日程相关工具：

1. 创建日程 - 用户想要记录、安排、计划某事
   例如："帮我记一下明天下午3点开会"、"安排一个日程"、"提醒我..."

2. 查询日程 - 用户想要查看、了解已有的日程安排
   例如："明天有什么安排？"、"查看我的日程"、"这几天有事吗？"

3. 修改日程 - 用户想要更改已有的日程
   例如："把那个会议改到后天"、"修改一下日程"

4. 删除日程 - 用户想要取消或删除日程
   例如："取消明天的会议"、"删除那个日程"

【重要】以下情况不要调用工具，直接正常对话：
- 闲聊、问候（如"你好"、"怎么样"）
- 知识问答（如"什么是AI"、"天气怎么样"）
- 其他与日程管理无关的所有话题

【对话风格】
- 友好、自然、简洁
- 不要主动推销日程功能
- 请用中文回复"""

    def __init__(self, zhipu_api_key: str, model: str = "glm-4"):
        """
        初始化 Agent 服务

        Args:
            zhipu_api_key: 智谱AI API密钥
            model: 模型名称 (glm-4, glm-4-plus, glm-4-flash 等)
        """
        self.api_key = zhipu_api_key
        self.model = model

        # 使用 LangChain 官方的 ZhipuAI 集成
        # 这会使用官方 API endpoint，支持资源包
        self.llm = ChatZhipuAI(
            model=model,
            temperature=0.7,
            zhipuai_api_key=zhipu_api_key,
        )

        logger.info(f"ScheduleAgentService 初始化成功，使用模型: {model}")

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

            # 创建工具集：通用工具 + 日程管理工具
            common_tools = get_common_tools()
            schedule_tools = create_schedule_tools(schedule_service, user_id)
            tools = common_tools + schedule_tools

            # 使用新的 create_agent API (LangChain 1.0)
            agent = create_agent(
                self.llm,
                tools=tools,
                system_prompt=self.SYSTEM_PROMPT
            )

            # 执行 Agent (使用异步调用)
            result = await agent.ainvoke({
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
