"""
智谱AI服务模块
调用智谱GLM大模型API进行对话
"""
from zai import ZhipuAiClient
import logging
from typing import List, Optional

from config import (
    ZHIPU_API_KEY,
    ZHIPU_MODEL,
    ZHIPU_TEMPERATURE,
    ZHIPU_MAX_TOKENS,
    DEFAULT_SYSTEM_PROMPT,
    CONTEXT_MEMORY_SIZE
)

logger = logging.getLogger(__name__)


class AIService:
    """智谱AI服务"""

    def __init__(self):
        self.api_key = ZHIPU_API_KEY
        self.model = ZHIPU_MODEL
        self.temperature = ZHIPU_TEMPERATURE
        self.max_tokens = ZHIPU_MAX_TOKENS

        # 用户对话历史 {user_id: [messages]}
        self.conversation_history: dict = {}

        # 初始化ZhipuAI客户端（使用官方SDK）
        try:
            self.client = ZhipuAiClient(api_key=self.api_key)
            logger.info("ZhipuAiClient客户端初始化成功")
        except Exception as e:
            logger.error(f"ZhipuAiClient客户端初始化失败: {e}")
            self.client = None

    async def chat(
        self,
        message: str,
        user_id: str,
        system_prompt: Optional[str] = None
    ) -> str:
        """
        发送消息到智谱AI并获取回复

        Args:
            message: 用户消息
            user_id: 用户ID（用于维护对话上下文）
            system_prompt: 系统提示词（可选）

        Returns:
            AI回复内容
        """
        if not self.client:
            logger.error("ZhipuAI客户端未初始化")
            return "抱歉，AI服务未初始化，请稍后再试。"

        try:
            # 获取或创建用户对话历史
            if user_id not in self.conversation_history:
                self.conversation_history[user_id] = []

            # 准备消息列表
            messages = []

            # 添加系统提示
            if system_prompt or DEFAULT_SYSTEM_PROMPT:
                messages.append({
                    "role": "system",
                    "content": system_prompt or DEFAULT_SYSTEM_PROMPT
                })

            # 添加历史对话
            history = self.conversation_history[user_id][-CONTEXT_MEMORY_SIZE:]
            messages.extend(history)

            # 添加当前用户消息
            messages.append({
                "role": "user",
                "content": message
            })

            logger.info(f"发送AI请求: user_id={user_id}, message_length={len(message)}")

            # 使用官方SDK调用
            response = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=self.temperature,
                max_tokens=self.max_tokens,
                stream=False
            )

            # 获取回复
            ai_reply = response.choices[0].message.content

            # 更新对话历史
            self.conversation_history[user_id].append({
                "role": "user",
                "content": message
            })
            self.conversation_history[user_id].append({
                "role": "assistant",
                "content": ai_reply
            })

            logger.info(f"AI回复成功: reply_length={len(ai_reply)}")
            return ai_reply

        except Exception as e:
            logger.error(f"调用智谱AI时出错: {e}", exc_info=True)
            # 检查是否是余额不足
            if "余额不足" in str(e) or "1113" in str(e):
                return "抱歉，AI服务余额不足，请充值API余额。"
            return "抱歉，AI服务出现错误，请稍后再试。"

    def clear_history(self, user_id: str) -> None:
        """
        清除指定用户的对话历史

        Args:
            user_id: 用户ID
        """
        if user_id in self.conversation_history:
            self.conversation_history[user_id] = []
            logger.info(f"已清除用户 {user_id} 的对话历史")

    def get_history(self, user_id: str) -> List[dict]:
        """
        获取指定用户的对话历史

        Args:
            user_id: 用户ID

        Returns:
            对话历史列表
        """
        return self.conversation_history.get(user_id, [])

    def set_system_prompt(self, user_id: str, prompt: str) -> None:
        """
        为指定用户设置自定义系统提示词

        Args:
            user_id: 用户ID
            prompt: 系统提示词
        """
        logger.info(f"为用户 {user_id} 设置自定义系统提示词: {prompt[:50]}...")
