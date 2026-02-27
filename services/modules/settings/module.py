"""
设置模块实现
统一管理所有设置项
"""
import logging
from typing import Type

from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from services.modules.base import BaseModule
from services.core.chat import SettingsAction

logger = logging.getLogger(__name__)


class SettingsModule(BaseModule):
    """设置管理模块"""

    module_id: str = "settings"
    module_name: str = "设置管理"
    module_description: str = "管理提醒设置、订阅设置等"

    @property
    def action_model(self) -> Type[BaseModel]:
        return SettingsAction

    async def execute(
        self,
        action: BaseModel,
        user_id: str,
        db_session: AsyncSession
    ) -> str:
        """执行设置操作"""
        if not isinstance(action, SettingsAction):
            return "设置操作格式错误"

        action_type = action.type
        target = action.target

        if action_type == "view":
            return await self._handle_view(action, user_id)
        elif action_type == "update":
            return await self._handle_update(action, user_id)
        else:
            return "未知的设置操作"

    def get_prompt_section(self) -> str:
        """设置模块不单独提供提示词，由 chat.py 统一管理"""
        return ""  # SETTINGS_PROMPT 已经在 chat.py 中

    async def _handle_view(self, action: SettingsAction, user_id: str) -> str:
        """查看设置"""
        # TODO: 从数据库读取用户设置
        lines = ["你的提醒设置：\n"]
        lines.append("📅 日程提醒：")
        lines.append("  - 每日提醒：已开启（08:00）")
        lines.append("  - 日程前提醒：已开启（提前30分钟）")
        lines.append("")
        lines.append("🎂 生日提醒：")
        lines.append("  - 生日提醒：已开启（提前7天）")
        lines.append("\n可以说「开启/关闭每日提醒」或「生日提前一周提醒」来修改")
        return "\n".join(lines)

    async def _handle_update(self, action: SettingsAction, user_id: str) -> str:
        """修改设置"""
        target = action.target

        # TODO: 实际保存到数据库
        if target == "daily_reminder":
            if action.daily_reminder_enabled is not None:
                if action.daily_reminder_enabled:
                    return "已开启每日提醒，将在每天 08:00 提醒你当天的日程"
                else:
                    return "已关闭每日提醒"
            elif action.daily_reminder_time:
                return f"已将每日提醒时间设置为 {action.daily_reminder_time}"
            else:
                return "请指定要修改的设置项"

        elif target == "pre_reminder":
            if action.pre_reminder_enabled is not None:
                if action.pre_reminder_enabled:
                    return "已开启日程前提醒，将在日程开始前 30 分钟提醒你"
                else:
                    return "已关闭日程前提醒"
            elif action.pre_reminder_minutes:
                return f"已将日程前提醒时间设置为提前 {action.pre_reminder_minutes} 分钟"
            else:
                return "请指定要修改的设置项"

        elif target == "birthday_reminder":
            if action.birthday_reminder_enabled is not None:
                if action.birthday_reminder_enabled:
                    return "已开启生日提醒，将在联系人生日提前 7 天提醒你"
                else:
                    return "已关闭生日提醒"
            elif action.birthday_reminder_days is not None:
                return f"已将生日提醒设置为提前 {action.birthday_reminder_days} 天提醒"
            else:
                return "请指定要修改的设置项"

        else:
            return "未知的设置项"


# 创建模块实例
settings_module = SettingsModule()
