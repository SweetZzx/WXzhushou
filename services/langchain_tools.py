"""
LangChain 工具定义
为日程助手提供可以被 Agent 调用的工具函数
"""
from langchain.tools import StructuredTool
from pydantic import BaseModel, Field
from typing import Optional
import logging
from datetime import datetime

logger = logging.getLogger(__name__)


# 工具参数模型
class CreateScheduleInput(BaseModel):
    """创建日程的输入参数"""
    title: str = Field(description="日程标题，如：开会、看病、健身")
    datetime: str = Field(description="日程时间，支持自然语言，如：明天下午3点、后天上午10点")
    description: Optional[str] = Field(default="", description="日程的详细描述")
    remind_before: Optional[int] = Field(default=0, description="提前多少分钟提醒")


class QuerySchedulesInput(BaseModel):
    """查询日程的输入参数"""
    date: Optional[str] = Field(default="今天", description="查询日期，如：今天、明天、本周、下周")


class DeleteScheduleInput(BaseModel):
    """删除日程的输入参数"""
    schedule_id: int = Field(description="要删除的日程ID")


class UpdateScheduleInput(BaseModel):
    """更新日程的输入参数"""
    schedule_id: int = Field(description="要更新的日程ID")
    title: Optional[str] = Field(default=None, description="新的日程标题")
    datetime: Optional[str] = Field(default=None, description="新的日程时间")


# 工具函数定义
class ScheduleTools:
    """日程工具集合"""

    def __init__(self, schedule_service, user_id: str):
        """
        初始化工具集合

        Args:
            schedule_service: ScheduleService 实例
            user_id: 当前用户ID
        """
        self.service = schedule_service
        self.user_id = user_id

    async def create_schedule(
        self,
        title: str,
        datetime: str,
        description: str = "",
        remind_before: int = 0
    ) -> str:
        """
        创建一个新的日程

        Args:
            title: 日程标题
            datetime: 日程时间
            description: 详细描述
            remind_before: 提前提醒分钟数

        Returns:
            操作结果消息
        """
        schedule = await self.service.create_schedule(
            user_id=self.user_id,
            title=title,
            time_str=datetime,
            description=description or None,
            remind_before=remind_before
        )

        if schedule:
            time_str = self.service.format_schedule(schedule).split('\n')[1]  # 获取时间行
            return f"✅ 日程创建成功！\n{self.service.format_schedule(schedule)}"
        else:
            return "❌ 创建日程失败，请检查时间格式是否正确。"

    async def query_schedules(self, date: str = "今天") -> str:
        """
        查询用户的日程列表

        Args:
            date: 查询日期范围

        Returns:
            日程列表消息
        """
        schedules = await self.service.list_schedules(
            user_id=self.user_id,
            date_str=date
        )

        if not schedules:
            return f"📭 {date}没有日程安排。"

        result = f"📋 {date}的日程：\n\n"
        for i, schedule in enumerate(schedules, 1):
            result += f"{i}. {self.service.format_schedule(schedule)}\n\n"

        return result.strip()

    async def delete_schedule(self, schedule_id: int) -> str:
        """
        删除指定的日程

        Args:
            schedule_id: 日程ID

        Returns:
            操作结果消息
        """
        success = await self.service.delete_schedule(schedule_id, self.user_id)
        if success:
            return f"✅ 已删除日程 (ID: {schedule_id})"
        else:
            return f"❌ 删除失败，未找到日程或无权操作 (ID: {schedule_id})"

    async def update_schedule(
        self,
        schedule_id: int,
        title: Optional[str] = None,
        datetime: Optional[str] = None
    ) -> str:
        """
        更新日程信息

        Args:
            schedule_id: 日程ID
            title: 新标题
            datetime: 新时间

        Returns:
            操作结果消息
        """
        schedule = await self.service.update_schedule(
            schedule_id=schedule_id,
            user_id=self.user_id,
            title=title,
            time_str=datetime
        )

        if schedule:
            return f"✅ 日程更新成功！\n{self.service.format_schedule(schedule)}"
        else:
            return f"❌ 更新失败，未找到日程或无权操作 (ID: {schedule_id})"

    def get_tools(self):
        """获取 LangChain 工具列表"""
        return [
            StructuredTool.from_function(
                coroutine=self.create_schedule,
                name="create_schedule",
                description="创建一个新的日程安排。使用自然语言描述时间和标题，如'明天下午3点开会'。",
                args_schema=CreateScheduleInput
            ),
            StructuredTool.from_function(
                coroutine=self.query_schedules,
                name="query_schedules",
                description="查询用户在指定日期的日程安排，支持'今天'、'明天'、'本周'等查询。",
                args_schema=QuerySchedulesInput
            ),
            StructuredTool.from_function(
                coroutine=self.delete_schedule,
                name="delete_schedule",
                description="删除指定的日程，需要提供日程ID。",
                args_schema=DeleteScheduleInput
            ),
            StructuredTool.from_function(
                coroutine=self.update_schedule,
                name="update_schedule",
                description="更新已存在的日程，可以修改标题或时间，需要提供日程ID。",
                args_schema=UpdateScheduleInput
            ),
        ]


def create_schedule_tools(schedule_service, user_id: str):
    """
    创建日程工具集（便捷函数）

    Args:
        schedule_service: ScheduleService 实例
        user_id: 当前用户ID

    Returns:
        LangChain 工具列表
    """
    tools = ScheduleTools(schedule_service, user_id)
    return tools.get_tools()
