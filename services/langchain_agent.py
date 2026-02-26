"""
日程 Agent 服务
聊天 + 意图检测 + 结构化执行
"""
import logging
import time
from collections import defaultdict

from services.schedule_executor import schedule_executor

logger = logging.getLogger(__name__)


class LangChainAgentService:
    """日程 Agent 服务"""

    def __init__(self):
        # 对话历史（user_id -> history list）
        self._history = defaultdict(list)

    async def process(self, message: str, user_id: str, db_session) -> str:
        """
        处理用户消息

        流程：
        1. LLM 聊天 + 检测意图
        2. 如果有日程意图，执行操作
        3. 返回回复（操作用模板，聊天用 AI 回复）
        """
        start_time = time.time()

        try:
            # 获取用户历史
            history = self._history.get(user_id, [])

            # 调用执行器处理
            response, ai_output = await schedule_executor.process(
                message=message,
                user_id=user_id,
                db_session=db_session,
                history=history
            )

            # 更新历史
            self._history[user_id].append({"role": "user", "content": message})
            self._history[user_id].append({"role": "assistant", "content": response})

            # 限制历史长度（保留最近 6 轮 = 12 条消息）
            if len(self._history[user_id]) > 12:
                self._history[user_id] = self._history[user_id][-12:]

            elapsed = time.time() - start_time
            has_action = "✅" if ai_output.action else "💬"
            logger.info(f"[Agent] {has_action} 耗时: {elapsed:.2f}s")

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
