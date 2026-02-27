"""
智能助手服务
聊天 + 意图检测 + 结构化执行（日程 + 联系人）
支持模块化动态加载
"""
import logging
import time
from collections import defaultdict
from typing import List

from services.core.chat import chat_service
from services.modules.registry import registry
from services.modules.subscription import SubscriptionService
from services.modules.settings.module import settings_module

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
        1. 获取用户订阅的模块
        2. LLM 聊天 + 检测意图
        3. 根据意图类型调用对应模块
        4. 返回回复
        """
        start_time = time.time()

        try:
            # 获取用户历史
            history = self._history.get(user_id, [])

            # 1. 获取用户已启用的模块
            enabled_modules = await registry.get_enabled_modules(user_id, db_session)

            # 2. 调用 LLM 获取意图
            ai_output = await chat_service.process(message, enabled_modules, history)

            # 3. 根据意图类型执行操作
            response = None
            action_type = "💬"

            # 处理设置操作（优先级最高）
            if ai_output.settings_action:
                response = await settings_module.execute(
                    ai_output.settings_action,
                    user_id,
                    db_session
                )
                action_type = "⚙️"

            # 处理订阅操作
            elif ai_output.subscription_action:
                response = await self._handle_subscription(
                    ai_output.subscription_action,
                    user_id,
                    db_session
                )
                action_type = "📋"

            # 处理日程操作
            elif ai_output.schedule_action:
                # 检查用户是否订阅了日程模块
                schedule_module = registry.get("schedule")
                if schedule_module and schedule_module in enabled_modules:
                    response = await schedule_module.execute(
                        ai_output.schedule_action,
                        user_id,
                        db_session
                    )
                    action_type = "📅"
                else:
                    response = "你还没有订阅日程功能，可以说「订阅日程」来开启"

            # 处理联系人操作
            elif ai_output.contact_action:
                # 检查用户是否订阅了联系人模块
                contact_module = registry.get("contact")
                if contact_module and contact_module in enabled_modules:
                    response = await contact_module.execute(
                        ai_output.contact_action,
                        user_id,
                        db_session
                    )
                    action_type = "👤"
                else:
                    response = "你还没有订阅联系人功能，可以说「订阅联系人」来开启"

            # 普通聊天
            else:
                response = ai_output.reply
                action_type = "💬"

            # 4. 更新历史
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

    async def _handle_subscription(self, action, user_id: str, db_session) -> str:
        """处理订阅操作"""
        subscription_service = SubscriptionService(db_session)
        action_type = action.type

        if action_type == "subscribe":
            # 订阅模块
            module_id = action.module_id
            if not module_id:
                return "请告诉我要订阅哪个模块，比如「订阅日程」"

            module = registry.get(module_id)
            if not module:
                return f"没有找到「{module_id}」模块"

            success = await subscription_service.subscribe(user_id, module_id)
            if success:
                return f"已订阅「{module.module_name}」功能"
            else:
                return "订阅失败，请稍后重试"

        elif action_type == "unsubscribe":
            # 取消订阅
            module_id = action.module_id
            if not module_id:
                return "请告诉我要取消订阅哪个模块，比如「取消订阅日程」"

            module = registry.get(module_id)
            if not module:
                return f"没有找到「{module_id}」模块"

            success = await subscription_service.unsubscribe(user_id, module_id)
            if success:
                return f"已取消订阅「{module.module_name}」功能"
            else:
                return "取消订阅失败，请稍后重试"

        elif action_type == "list_subscriptions":
            # 查看订阅状态
            status = await subscription_service.get_subscription_status(user_id)

            lines = ["你的功能订阅状态：\n"]
            for module in registry.get_all():
                enabled = status.get(module.module_id, True)
                status_text = "已开启" if enabled else "已关闭"
                lines.append(f"- {module.module_name}：{status_text}")

            lines.append("\n可以说「订阅日程」或「取消订阅日程」来管理")
            return "\n".join(lines)

        elif action_type == "list_modules":
            # 列出所有可用模块
            modules = registry.get_all()

            lines = ["目前可用的功能模块：\n"]
            for module in modules:
                lines.append(f"- {module.module_name}：{module.module_description}")

            lines.append("\n可以说「订阅XX」或「取消订阅XX」来管理")
            return "\n".join(lines)

        else:
            return "未知的订阅操作"

    async def chat(self, message: str, user_id: str = "default") -> str:
        """普通对话"""
        return await self.process(message, user_id, None)

    def clear_history(self, user_id: str):
        """清除对话历史"""
        self._history[user_id] = []
        logger.info(f"已清除用户 {user_id} 的对话历史")


# 全局实例
langchain_agent = LangChainAgentService()
