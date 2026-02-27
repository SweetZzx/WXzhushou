"""
聊天 + 意图检测服务
LLM 负责自然对话 + 检测日程/联系人意图 + 提取结构化数据
支持模块化动态生成 SYSTEM_PROMPT
"""
import logging
import json
import re
from typing import Optional, List, TYPE_CHECKING
from datetime import datetime
from pydantic import BaseModel, Field

from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
from services.core.llm import get_llm

if TYPE_CHECKING:
    from services.modules.base import BaseModule

logger = logging.getLogger(__name__)

# ============================================
# Pydantic 输出模型
# ============================================

class ScheduleAction(BaseModel):
    """日程操作"""
    type: str = Field(default="", description="操作类型: create/query/update/delete")
    title: Optional[str] = Field(default=None, description="日程标题")
    time: Optional[str] = Field(default=None, description="时间描述")
    target: Optional[str] = Field(default=None, description="目标日程ID或关键词")
    date: Optional[str] = Field(default=None, description="查询日期")


class ContactAction(BaseModel):
    """联系人操作"""
    type: str = Field(default="", description="操作类型: contact_create/contact_query/contact_update/contact_delete")
    name: Optional[str] = Field(default=None, description="联系人姓名")
    phone: Optional[str] = Field(default=None, description="电话号码")
    birthday: Optional[str] = Field(default=None, description="生日，格式: MM-DD")
    remark: Optional[str] = Field(default=None, description="备注（如：大学同学、前同事）")
    extra: Optional[str] = Field(default=None, description="其他信息（爱好、QQ、邮箱、地址等）")
    query_field: Optional[str] = Field(default=None, description="查询的字段类型: phone/birthday/all")


class SubscriptionAction(BaseModel):
    """订阅操作"""
    type: str = Field(default="", description="操作类型: subscribe/unsubscribe/list_modules/list_subscriptions")
    module_id: Optional[str] = Field(default=None, description="模块ID: schedule/contact")


class SettingsAction(BaseModel):
    """设置操作"""
    type: str = Field(default="", description="操作类型: view/update")
    target: str = Field(default="", description="设置目标: all/daily_reminder/pre_reminder/birthday_reminder")
    # 每日提醒设置
    daily_reminder_enabled: Optional[bool] = Field(default=None, description="是否开启每日提醒")
    daily_reminder_time: Optional[str] = Field(default=None, description="每日提醒时间，如08:00")
    # 日程前提醒设置
    pre_reminder_enabled: Optional[bool] = Field(default=None, description="是否开启日程前提醒")
    pre_reminder_minutes: Optional[int] = Field(default=None, description="日程前多少分钟提醒")
    # 生日提醒设置
    birthday_reminder_enabled: Optional[bool] = Field(default=None, description="是否开启生日提醒")
    birthday_reminder_days: Optional[int] = Field(default=None, description="生日提前多少天提醒")


class AIOutput(BaseModel):
    """AI 输出格式"""
    reply: str = Field(description="给用户的回复内容")
    schedule_action: Optional[ScheduleAction] = Field(default=None, description="日程操作")
    contact_action: Optional[ContactAction] = Field(default=None, description="联系人操作")
    subscription_action: Optional[SubscriptionAction] = Field(default=None, description="订阅操作")
    settings_action: Optional[SettingsAction] = Field(default=None, description="设置操作")

    @property
    def action(self):
        """兼容旧代码的属性"""
        return self.schedule_action or self.contact_action or self.subscription_action or self.settings_action

    @property
    def action_type(self) -> str:
        """获取操作类型"""
        if self.schedule_action:
            return self.schedule_action.type
        if self.contact_action:
            return self.contact_action.type
        if self.subscription_action:
            return self.subscription_action.type
        if self.settings_action:
            return self.settings_action.type
        return ""


# ============================================
# SYSTEM_PROMPT 模板
# ============================================

BASE_PROMPT = """你是一个智能助手，帮助用户管理日程和联系人。

【重要规则】
你必须且只能输出 JSON 格式，不要输出任何其他内容！
不要复述用户的请求，不要输出错误信息，只输出 JSON！

【当前时间】
{current_time}
"""

SUBSCRIPTION_PROMPT = """
【订阅管理】
用户可以订阅或取消订阅功能模块：
- "订阅日程" / "开启日程功能" → 订阅日程模块，module_id: "schedule"
- "取消订阅日程" / "关闭日程功能" → 取消订阅日程模块
- "订阅联系人" / "开启联系人功能" → 订阅联系人模块，module_id: "contact"
- "取消订阅联系人" / "关闭联系人功能" → 取消订阅联系人模块
- "我的订阅" / "我订阅了哪些功能" → 查看订阅状态
- "可用的模块" / "有什么功能" → 查看所有可用模块

订阅操作类型：
- subscribe: 订阅模块
- unsubscribe: 取消订阅模块
- list_subscriptions: 查看我的订阅
- list_modules: 查看可用模块
"""

SETTINGS_PROMPT = """
【设置管理】
- "设置" / "提醒设置" / "设置提醒" → type: "view", target: "all"
- "开启每日提醒" → type: "update", target: "daily_reminder", daily_reminder_enabled: true
- "关闭每日提醒" → type: "update", target: "daily_reminder", daily_reminder_enabled: false
- "设置每日提醒时间为8点" → type: "update", target: "daily_reminder", daily_reminder_time: "08:00"
- "开启日程前提醒" → type: "update", target: "pre_reminder", pre_reminder_enabled: true
- "关闭日程前提醒" → type: "update", target: "pre_reminder", pre_reminder_enabled: false
- "开启生日提醒" → type: "update", target: "birthday_reminder", birthday_reminder_enabled: true
- "关闭生日提醒" → type: "update", target: "birthday_reminder", birthday_reminder_enabled: false
- "生日提前一周提醒" / "生日提前7天提醒" → type: "update", target: "birthday_reminder", birthday_reminder_days: 7
- "生日提前3天提醒" → type: "update", target: "birthday_reminder", birthday_reminder_days: 3
"""

OUTPUT_FORMAT_PROMPT = """
【输出格式 - 必须是有效 JSON】
每次输出都必须包含以下 5 个字段，缺一不可：
- reply: 你的回复内容
- schedule_action: 日程操作（无则为 null）
- contact_action: 联系人操作（无则为 null）
- subscription_action: 订阅操作（无则为 null）
- settings_action: 设置操作（无则为 null）

```json
{{
  "reply": "你的回复",
  "schedule_action": null,
  "contact_action": null,
  "subscription_action": null,
  "settings_action": null
}}
```

【再次强调】
1. 必须输出完整的 5 个字段，不能省略任何字段！
2. 无论用户问什么，你都只能输出 JSON 格式！
3. 不要输出「没有找到」之类的文字，那是系统的工作。
"""

# 示例（通用）
EXAMPLES_PROMPT = """
【示例】
用户: "你好呀"
输出: {{"reply": "你好！有什么可以帮你的？", "schedule_action": null, "contact_action": null, "subscription_action": null, "settings_action": null}}

用户: "设置提醒"
输出: {{"reply": "让我看看...", "schedule_action": null, "contact_action": null, "subscription_action": null, "settings_action": {{"type": "view", "target": "all"}}}}

用户: "开启每日提醒"
输出: {{"reply": "好的，帮你开启每日提醒", "schedule_action": null, "contact_action": null, "subscription_action": null, "settings_action": {{"type": "update", "target": "daily_reminder", "daily_reminder_enabled": true}}}}

用户: "明天有什么安排"
输出: {{"reply": "让我看看...", "schedule_action": {{"type": "query", "date": "明天"}}, "contact_action": null, "subscription_action": null, "settings_action": null}}

用户: "小明的电话"
输出: {{"reply": "让我看看...", "schedule_action": null, "contact_action": {{"type": "contact_query", "name": "小明", "query_field": "phone"}}, "subscription_action": null, "settings_action": null}}

用户: "小明的生日"
输出: {{"reply": "让我看看...", "schedule_action": null, "contact_action": {{"type": "contact_query", "name": "小明", "query_field": "birthday"}}, "subscription_action": null, "settings_action": null}}

用户: "小明的电话是13812345678"
输出: {{"reply": "好的，帮你记录", "schedule_action": null, "contact_action": {{"type": "contact_create", "name": "小明", "phone": "13812345678"}}, "subscription_action": null, "settings_action": null}}

用户: "我的订阅"
输出: {{"reply": "让我看看...", "schedule_action": null, "contact_action": null, "subscription_action": {{"type": "list_subscriptions"}}, "settings_action": null}}

用户: "有什么功能"
输出: {{"reply": "让我看看...", "schedule_action": null, "contact_action": null, "subscription_action": {{"type": "list_modules"}}, "settings_action": null}}

用户: "关闭日程功能"
输出: {{"reply": "好的，帮你关闭日程功能", "schedule_action": null, "contact_action": null, "subscription_action": {{"type": "unsubscribe", "module_id": "schedule"}}, "settings_action": null}}

用户: "开启生日提醒"
输出: {{"reply": "好的，帮你开启生日提醒", "schedule_action": null, "contact_action": null, "subscription_action": null, "settings_action": {{"type": "update", "target": "birthday_reminder", "birthday_reminder_enabled": true}}}}

用户: "生日提前一周提醒"
输出: {{"reply": "好的，帮你设置生日提前7天提醒", "schedule_action": null, "contact_action": null, "subscription_action": null, "settings_action": {{"type": "update", "target": "birthday_reminder", "birthday_reminder_days": 7}}}}
"""


def build_system_prompt(
    enabled_modules: List["BaseModule"],
    current_time: str
) -> str:
    """
    根据用户订阅的模块动态构建 SYSTEM_PROMPT

    Args:
        enabled_modules: 用户已启用的模块列表
        current_time: 当前时间字符串

    Returns:
        完整的 SYSTEM_PROMPT
    """
    parts = [
        BASE_PROMPT.format(current_time=current_time)
    ]

    # 先添加各模块的提示词片段（优先级更高）
    for module in enabled_modules:
        prompt_section = module.get_prompt_section()
        if prompt_section:
            parts.append(prompt_section)

    # 添加设置管理提示词（优先级高于订阅管理）
    parts.append(SETTINGS_PROMPT)

    # 再添加订阅管理提示词
    parts.append(SUBSCRIPTION_PROMPT)

    parts.append(OUTPUT_FORMAT_PROMPT)
    parts.append(EXAMPLES_PROMPT)

    return "\n".join(parts)


class ChatWithActionService:
    """聊天 + 意图检测服务"""

    def __init__(self):
        self.llm = get_llm(temperature=0.7)

    async def process(
        self,
        message: str,
        enabled_modules: List["BaseModule"] = None,
        history: List[dict] = None
    ) -> AIOutput:
        """
        处理用户消息

        Args:
            message: 用户消息
            enabled_modules: 用户已启用的模块列表
            history: 对话历史 [{"role": "user/assistant", "content": "..."}]

        Returns:
            AIOutput: 包含 reply 和可选的 action
        """
        try:
            current_time = datetime.now().strftime("%Y年%m月%d日 %H:%M (%A)")

            # 动态构建 SYSTEM_PROMPT
            enabled_modules = enabled_modules or []
            system_prompt = build_system_prompt(enabled_modules, current_time)

            # 构建消息
            messages = [SystemMessage(content=system_prompt)]

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
            elif result.settings_action:
                logger.info(f"[设置意图] type={result.settings_action.type}, target={result.settings_action.target}")
            elif result.subscription_action:
                logger.info(f"[订阅意图] type={result.subscription_action.type}, module={result.subscription_action.module_id}")
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
            subscription_action = None
            settings_action = None

            # 兼容旧格式（只有 action 字段）
            if data.get("action") and isinstance(data["action"], dict):
                action_type = data["action"].get("type", "")
                if action_type.startswith("contact"):
                    contact_action = ContactAction(**data["action"])
                elif action_type in ["subscribe", "unsubscribe", "list_modules", "list_subscriptions"]:
                    subscription_action = SubscriptionAction(**data["action"])
                elif action_type in ["view", "update"]:
                    settings_action = SettingsAction(**data["action"])
                else:
                    schedule_action = ScheduleAction(**data["action"])

            # 新格式
            if data.get("schedule_action") and isinstance(data["schedule_action"], dict):
                schedule_action = ScheduleAction(**data["schedule_action"])
            if data.get("contact_action") and isinstance(data["contact_action"], dict):
                contact_action = ContactAction(**data["contact_action"])
            if data.get("subscription_action") and isinstance(data["subscription_action"], dict):
                subscription_action = SubscriptionAction(**data["subscription_action"])
            if data.get("settings_action") and isinstance(data["settings_action"], dict):
                settings_action = SettingsAction(**data["settings_action"])

            # 日志记录解析结果
            if schedule_action:
                logger.info(f"[JSON解析] 日程操作: type={schedule_action.type}")
            if contact_action:
                logger.info(f"[JSON解析] 联系人操作: type={contact_action.type}, name={contact_action.name}")
            if subscription_action:
                logger.info(f"[JSON解析] 订阅操作: type={subscription_action.type}")
            if settings_action:
                logger.info(f"[JSON解析] 设置操作: type={settings_action.type}, target={settings_action.target}")

            return AIOutput(
                reply=data.get("reply", ""),
                schedule_action=schedule_action,
                contact_action=contact_action,
                subscription_action=subscription_action,
                settings_action=settings_action
            )

        except json.JSONDecodeError as e:
            logger.warning(f"JSON 解析失败: {e}, 原始内容: {raw_content[:200]}")
            return AIOutput(reply=raw_content, schedule_action=None, contact_action=None)

        except Exception as e:
            logger.error(f"解析输出失败: {e}")
            return AIOutput(reply="抱歉，我没太理解", schedule_action=None, contact_action=None)


# 全局实例
chat_service = ChatWithActionService()
