"""
聊天 + 意图检测服务
LLM 负责自然对话 + 检测日程意图 + 提取结构化数据
"""
import logging
import json
import re
from typing import Optional, List
from datetime import datetime
from pydantic import BaseModel, Field

from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
from services.langchain_llm import get_llm

logger = logging.getLogger(__name__)

# ============================================
# Pydantic 输出模型
# ============================================

class ScheduleAction(BaseModel):
    """日程操作"""
    type: str = Field(default="", description="操作类型: create/query/update/delete/settings/update_settings")
    title: Optional[str] = Field(default=None, description="日程标题")
    time: Optional[str] = Field(default=None, description="时间描述")
    target: Optional[str] = Field(default=None, description="目标日程ID或关键词")
    date: Optional[str] = Field(default=None, description="查询日期")
    # 设置相关
    daily_reminder_enabled: Optional[bool] = Field(default=None, description="是否开启每日提醒")
    daily_reminder_time: Optional[str] = Field(default=None, description="每日提醒时间，如08:00")
    pre_reminder_enabled: Optional[bool] = Field(default=None, description="是否开启日程前提醒")
    pre_reminder_minutes: Optional[int] = Field(default=None, description="日程前多少分钟提醒")


class AIOutput(BaseModel):
    """AI 输出格式"""
    reply: str = Field(description="给用户的回复内容")
    action: Optional[ScheduleAction] = Field(default=None, description="日程操作（如果检测到）")


# ============================================
# 系统提示词
# ============================================

SYSTEM_PROMPT = """你是一个日程管理助手，同时也是用户的好朋友。

【你的职责】
1. 和用户自然聊天，像朋友一样
2. 在对话中检测用户是否有日程相关的意图
3. 如果有，提取结构化信息并按 JSON 格式输出

【日程意图判断标准】
只要消息包含「时间 + 事件」，就应该创建日程，不要追问细节：
- "下周五看电影" → 创建（时间：下周五，事件：看电影）
- "明天开会" → 创建（时间：明天，事件：开会）
- "3号考试" → 创建（时间：3号，事件：考试）

【操作类型】
- create: 创建日程（时间+事件齐全时立即创建，不追问）
- query: 查询日程（"明天有什么安排"、"我的日程"）
- update: 修改日程（"改成3点"、"推迟半小时"）
- delete: 删除日程（"删除这个"、"取消明天的"）
- settings: 查看提醒设置（"我的设置"、"提醒设置"）
- update_settings: 修改提醒设置（"把每日提醒改成7点"、"关闭日程前提醒"）

【输出格式 - 必须是有效 JSON】
```json
{{
  "reply": "你的回复内容",
  "action": null
}}
```

或者有日程操作时：
```json
{{
  "reply": "简短确认",
  "action": {{
    "type": "create",
    "title": "看电影",
    "time": "下周五"
  }}
}}
```

【当前时间】
{current_time}

【示例】
用户: "下周五看电影"
输出: {{"reply": "好嘞，帮你记下了！", "action": {{"type": "create", "title": "看电影", "time": "下周五"}}}}

用户: "明天有什么安排"
输出: {{"reply": "让我看看...", "action": {{"type": "query", "date": "明天"}}}}

用户: "你好呀"
输出: {{"reply": "你好！有什么可以帮你的？", "action": null}}

用户: "改成下午三点"
输出: {{"reply": "好的", "action": {{"type": "update", "time": "下午三点"}}}}

用户: "我的设置"
输出: {{"reply": "让我看看...", "action": {{"type": "settings"}}}}

用户: "把每日提醒改成7点"
输出: {{"reply": "好的", "action": {{"type": "update_settings", "daily_reminder_time": "07:00"}}}}

用户: "关闭每日提醒"
输出: {{"reply": "好的，已为你关闭每日提醒", "action": {{"type": "update_settings", "daily_reminder_enabled": false}}}}

用户: "开启日程前提醒"
输出: {{"reply": "好的", "action": {{"type": "update_settings", "pre_reminder_enabled": true}}}}

用户: "提前1小时提醒"
输出: {{"reply": "好的", "action": {{"type": "update_settings", "pre_reminder_minutes": 60}}}}

请只输出 JSON，不要输出其他内容。"""


class ChatWithActionService:
    """聊天 + 意图检测服务"""

    def __init__(self):
        self.llm = get_llm(temperature=0.7)

    async def process(
        self,
        message: str,
        history: List[dict] = None
    ) -> AIOutput:
        """
        处理用户消息

        Args:
            message: 用户消息
            history: 对话历史 [{"role": "user/assistant", "content": "..."}]

        Returns:
            AIOutput: 包含 reply 和可选的 action
        """
        try:
            current_time = datetime.now().strftime("%Y年%m月%d日 %H:%M (%A)")

            # 构建消息
            messages = [
                SystemMessage(content=SYSTEM_PROMPT.format(current_time=current_time))
            ]

            # 添加历史
            if history:
                for msg in history[-6:]:  # 最近3轮
                    if msg["role"] == "user":
                        messages.append(HumanMessage(content=msg["content"]))
                    else:
                        messages.append(AIMessage(content=msg["content"]))

            # 添加当前消息
            messages.append(HumanMessage(content=message))

            # 调用 LLM
            response = await self.llm.ainvoke(messages)
            raw_content = response.content.strip()

            # 解析 JSON
            result = self._parse_json_output(raw_content)

            # 记录日志
            if result.action:
                logger.info(f"[意图检测] type={result.action.type}, data={result.action.model_dump(exclude_none=True)}")
            else:
                logger.info(f"[普通聊天] {result.reply[:30] if result.reply else 'N/A'}...")

            return result

        except Exception as e:
            logger.error(f"处理失败: {e}", exc_info=True)
            return AIOutput(reply="抱歉，我刚才走神了，能再说一遍吗？", action=None)

    def _parse_json_output(self, raw_content: str) -> AIOutput:
        """解析 LLM 返回的 JSON"""
        try:
            # 尝试直接解析
            content = raw_content

            # 如果包含 ```json 代码块，提取内容
            if "```json" in content:
                match = re.search(r"```json\s*(.*?)\s*```", content, re.DOTALL)
                if match:
                    content = match.group(1)
            elif "```" in content:
                match = re.search(r"```\s*(.*?)\s*```", content, re.DOTALL)
                if match:
                    content = match.group(1)

            # 解析 JSON
            data = json.loads(content.strip())

            # 构建 AIOutput
            action = None
            if data.get("action") and isinstance(data["action"], dict):
                action = ScheduleAction(**data["action"])

            return AIOutput(
                reply=data.get("reply", ""),
                action=action
            )

        except json.JSONDecodeError as e:
            logger.warning(f"JSON 解析失败: {e}, 原始内容: {raw_content[:100]}")
            # 如果解析失败，把原始内容当作回复
            return AIOutput(reply=raw_content, action=None)

        except Exception as e:
            logger.error(f"解析输出失败: {e}")
            return AIOutput(reply="抱歉，我没太理解", action=None)


# 全局实例
chat_service = ChatWithActionService()
