"""
模块基类
定义模块的标准接口
"""
from abc import ABC, abstractmethod
from typing import Type, Optional, List

from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession


class BaseModule(ABC):
    """
    模块基类

    所有功能模块都需要继承此类并实现抽象方法
    """

    # 模块元信息（子类必须覆盖）
    module_id: str = ""           # 模块标识（如 "schedule", "contact"）
    module_name: str = ""         # 模块名称（如 "日程管理"）
    module_description: str = ""  # 模块描述

    @property
    @abstractmethod
    def action_model(self) -> Type[BaseModel]:
        """
        返回模块的 Action Pydantic 模型

        Returns:
            Action 模型类（如 ScheduleAction, ContactAction）
        """
        pass

    @abstractmethod
    async def execute(
        self,
        action: BaseModel,
        user_id: str,
        db_session: AsyncSession
    ) -> str:
        """
        执行模块操作

        Args:
            action: 操作数据（如 ScheduleAction, ContactAction）
            user_id: 用户ID
            db_session: 数据库会话

        Returns:
            执行结果（给用户的回复）
        """
        pass

    @abstractmethod
    def get_prompt_section(self) -> str:
        """
        返回该模块的 SYSTEM_PROMPT 片段

        这部分会被动态拼接到完整的 SYSTEM_PROMPT 中

        Returns:
            模块相关的提示词（意图判断规则、示例等）
        """
        pass

    def get_reminders(self) -> List["BaseReminder"]:
        """
        返回该模块的提醒服务列表

        子类可以覆盖此方法，返回模块相关的提醒服务

        Returns:
            提醒服务列表（默认为空）
        """
        return []

    def get_action_field_name(self) -> str:
        """
        获取 Action 在 AIOutput 中的字段名

        Returns:
            字段名（如 "schedule_action", "contact_action"）
        """
        return f"{self.module_id}_action"

    def __repr__(self) -> str:
        return f"<Module {self.module_id}: {self.module_name}>"


# 避免循环导入
from services.reminder.base import BaseReminder

