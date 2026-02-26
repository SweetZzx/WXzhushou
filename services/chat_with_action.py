"""
聊天 + 意图检测服务
LLM 负责自然对话 + 检测日程/联系人意图 + 提取结构化数据
"""
import logging
import json
import re
from typing import Optional, List, Union
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


class ContactAction(BaseModel):
    """联系人操作"""
    type: str = Field(default="", description="操作类型: contact_create/contact_query/contact_update/contact_delete")
    name: Optional[str] = Field(default=None, description="联系人姓名")
    phone: Optional[str] = Field(default=None, description="电话号码")
    birthday: Optional[str] = Field(default=None, description="生日，格式: MM-DD")
    remark: Optional[str] = Field(default=None, description="备注（如：大学同学、前同事）")
    extra: Optional[str] = Field(default=None, description="其他信息（爱好、QQ、邮箱、地址等）")
    query_field: Optional[str] = Field(default=None, description="查询的字段类型: phone/birthday/all，例如'电话是多少'为phone，'生日是什么'为birthday，'所有信息'为all或不填")


class AIOutput(BaseModel):
    """AI 输出格式"""
    reply: str = Field(description="给用户的回复内容")
    schedule_action: Optional[ScheduleAction] = Field(default=None, description="日程操作")
    contact_action: Optional[ContactAction] = Field(default=None, description="联系人操作")

    @property
    def action(self):
        """兼容旧代码的属性"""
        return self.schedule_action or self.contact_action

    @property
    def action_type(self) -> str:
        """获取操作类型"""
        if self.schedule_action:
            return self.schedule_action.type
        if self.contact_action:
            return self.contact_action.type
        return ""


# ============================================
# 系统提示词
# ============================================

SYSTEM_PROMPT = """你是一个智能助手，帮助用户管理日程和联系人。

【你的职责】
1. 和用户自然聊天，像朋友一样
2. 在对话中检测用户的意图（日程相关或联系人相关）
3. 如果有明确意图，提取结构化信息并按 JSON 格式输出

【日程意图判断】
消息包含「时间 + 事件」时创建日程：
- "下周五看电影" → 创建日程
- "明天开会" → 创建日程
- "明天有什么安排" → 查询日程（date: "明天"）
- "所有日程" / "全部日程" / "我有哪些日程" → 查询日程（date: "所有"）

【联系人意图判断】
只要消息提到某人的信息（电话、生日、爱好、QQ、邮箱、地址等），就应该创建/更新联系人：
- "小明的电话是13812345678" → 创建联系人，记录电话
- "小明生日是3月15号" → 创建/更新联系人，记录生日
- "小明喜欢打篮球" → 创建/更新联系人，记录爱好到extra
- "小明QQ是12345678" → 创建/更新联系人，记录QQ到extra
- "小明邮箱是xx@qq.com" → 创建/更新联系人，记录邮箱到extra
- "小明住在北京" → 创建/更新联系人，记录地址到extra
- "小明的电话是多少" → 查询联系人，query_field: "phone"
- "小明的生日是什么时候" → 查询联系人，query_field: "birthday"
- "小明的信息" / "小明的所有信息" → 查询联系人，query_field: "all" 或不填
- "我记录了哪些联系人" → 列出所有联系人

【操作类型】
日程操作：
- create: 创建日程
- query: 查询日程
- update: 修改日程
- delete: 删除日程
- settings/update_settings: 查看或修改设置

联系人操作：
- contact_create: 添加联系人（有姓名+信息时自动创建或更新）
- contact_query: 查询联系人
- contact_delete: 删除联系人

【输出格式 - 必须是有效 JSON】
```json
{{
  "reply": "你的回复",
  "schedule_action": null,
  "contact_action": null
}}
```

【当前时间】
{current_time}

【示例】
用户: "下周五看电影"
输出: {{"reply": "好嘞，帮你记下了！", "schedule_action": {{"type": "create", "title": "看电影", "time": "下周五"}}, "contact_action": null}}

用户: "小明的电话是13812345678"
输出: {{"reply": "好的，帮你记下小明的电话", "schedule_action": null, "contact_action": {{"type": "contact_create", "name": "小明", "phone": "13812345678"}}}}

用户: "小明生日是3月15号"
输出: {{"reply": "好的，记下了", "schedule_action": null, "contact_action": {{"type": "contact_create", "name": "小明", "birthday": "03-15"}}}}

用户: "小明喜欢打篮球和看电影"
输出: {{"reply": "好的，记下了小明的爱好", "schedule_action": null, "contact_action": {{"type": "contact_create", "name": "小明", "extra": "爱好：打篮球、看电影"}}}}

用户: "小明QQ是12345678，邮箱是xiaoming@qq.com"
输出: {{"reply": "好的，记下了", "schedule_action": null, "contact_action": {{"type": "contact_create", "name": "小明", "extra": "QQ：12345678，邮箱：xiaoming@qq.com"}}}}

用户: "小明的电话是多少"
输出: {{"reply": "让我查一下...", "schedule_action": null, "contact_action": {{"type": "contact_query", "name": "小明", "query_field": "phone"}}}}

用户: "小明的生日是什么时候"
输出: {{"reply": "让我查一下...", "schedule_action": null, "contact_action": {{"type": "contact_query", "name": "小明", "query_field": "birthday"}}}}

用户: "小明的所有信息"
输出: {{"reply": "让我查一下...", "schedule_action": null, "contact_action": {{"type": "contact_query", "name": "小明", "query_field": "all"}}}}

用户: "我记录了哪些联系人"
输出: {{"reply": "让我看看...", "schedule_action": null, "contact_action": {{"type": "contact_query"}}}}

用户: "你好呀"
输出: {{"reply": "你好！有什么可以帮你的？", "schedule_action": null, "contact_action": null}}

用户: "明天有什么安排"
输出: {{"reply": "让我看看...", "schedule_action": {{"type": "query", "date": "明天"}}, "contact_action": null}}

用户: "我所有的日程有哪些" / "所有日程" / "全部日程"
输出: {{"reply": "让我看看...", "schedule_action": {{"type": "query", "date": "所有"}}, "contact_action": null}}

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
            if result.schedule_action:
                logger.info(f"[日程意图] type={result.schedule_action.type}")
            elif result.contact_action:
                logger.info(f"[联系人意图] type={result.contact_action.type}, name={result.contact_action.name}")
            else:
                logger.info(f"[普通聊天] {result.reply[:30] if result.reply else 'N/A'}...")

            return result

        except Exception as e:
            logger.error(f"处理失败: {e}", exc_info=True)
            return AIOutput(reply="抱歉，我刚才走神了，能再说一遍吗？")

    def _parse_json_output(self, raw_content: str) -> AIOutput:
        """解析 LLM 返回的 JSON"""
        try:
            content = raw_content.strip()

            # 如果包含 ```json 代码块，提取内容
            if "```json" in content:
                match = re.search(r"```json\s*(.*?)\s*```", content, re.DOTALL)
                if match:
                    content = match.group(1).strip()
            elif "```" in content:
                match = re.search(r"```\s*(.*?)\s*```", content, re.DOTALL)
                if match:
                    content = match.group(1).strip()

            # 如果内容不直接是 JSON 对象，尝试提取第一个 JSON 对象
            if not content.startswith("{"):
                # 尝试找到第一个 { 和最后一个 }
                start = content.find("{")
                end = content.rfind("}")
                if start != -1 and end != -1 and end > start:
                    content = content[start:end+1]
                    logger.debug(f"提取 JSON: {content[:100]}...")

            # 解析 JSON
            data = json.loads(content.strip())

            # 构建 AIOutput
            schedule_action = None
            contact_action = None

            # 兼容旧格式（只有 action 字段）
            if data.get("action") and isinstance(data["action"], dict):
                action_type = data["action"].get("type", "")
                if action_type.startswith("contact"):
                    contact_action = ContactAction(**data["action"])
                else:
                    schedule_action = ScheduleAction(**data["action"])

            # 新格式
            if data.get("schedule_action") and isinstance(data["schedule_action"], dict):
                schedule_action = ScheduleAction(**data["schedule_action"])
            if data.get("contact_action") and isinstance(data["contact_action"], dict):
                contact_action = ContactAction(**data["contact_action"])

            # 日志记录解析结果
            if schedule_action:
                logger.info(f"[JSON解析] 日程操作: type={schedule_action.type}")
            if contact_action:
                logger.info(f"[JSON解析] 联系人操作: type={contact_action.type}, name={contact_action.name}")

            return AIOutput(
                reply=data.get("reply", ""),
                schedule_action=schedule_action,
                contact_action=contact_action
            )

        except json.JSONDecodeError as e:
            logger.warning(f"JSON 解析失败: {e}, 原始内容: {raw_content[:200]}")
            return AIOutput(reply=raw_content, schedule_action=None, contact_action=None)

        except Exception as e:
            logger.error(f"解析输出失败: {e}")
            return AIOutput(reply="抱歉，我没太理解", schedule_action=None, contact_action=None)


# 全局实例
chat_service = ChatWithActionService()
