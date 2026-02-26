"""
智能助手服务
聊天 + 意图检测 + 结构化执行（日程 + 联系人）
"""
import logging
import time
from collections import defaultdict

from services.chat_with_action import chat_service
from services.schedule_executor import schedule_executor
from services.contact_executor import contact_executor

logger = logging.getLogger(__name__)


class LangChainAgentService:
    """智能助手服务"""

    def __init__(self):
        # 对话历史（user_id -> history list）
        self._history = defaultdict(list)

    async def process(self, message: str, user_id: str, db_session) -> str:
        """
        处理用户消息

        流程：
        1. LLM 聊天 + 检测意图
        2. 根据意图类型调用对应执行器
        3. 返回回复
        """
        start_time = time.time()

        try:
            # 获取用户历史
            history = self._history.get(user_id, [])

            # 1. 调用 LLM 获取意图
            ai_output = await chat_service.process(message, history)

            # 2. 根据意图类型执行操作
            if ai_output.schedule_action:
                # 日程操作
                response = await schedule_executor.execute(
                    ai_output.schedule_action,
                    user_id,
                    db_session,
                    ai_output.reply
                )
                action_type = "📅"

            elif ai_output.contact_action:
                # 联系人操作
                response = await contact_executor.process(
                    ai_output.contact_action,
                    user_id,
                    db_session
                )
                action_type = "👤"

            else:
                # 普通聊天
                response = ai_output.reply
                action_type = "💬"

            # 3. 更新历史
            self._history[user_id].append({"role": "user", "content": message})
            self._history[user_id].append({"role": "assistant", "content": response})

            # 限制历史长度
            if len(self._history[user_id]) > 12:
                self._history[user_id] = self._history[user_id][-12:]

            elapsed = time.time() - start_time
            logger.info(f"[Agent] {action_type} 耗时: {elapsed:.2f}s")

            return response

        except Exception as e:
            logger.error(f"处理失败: {e}", exc_info=True)
            return f"抱歉，处理请求时出错：{str(e)}"

    async def chat(self, message: str, user_id: str = "default") -> str:
        """普通对话"""
        return await self.process(message, user_id, None)

    def clear_history(self, user_id: str):
        """清除对话历史"""
        self._history[user_id] = []
        logger.info(f"已清除用户 {user_id} 的对话历史")


# 全局实例
langchain_agent = LangChainAgentService()
