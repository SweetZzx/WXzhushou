"""
LangChain 工具定义
为日程助手提供可以被 Agent 调用的工具函数
使用 LangChain 1.0 的 @tool 装饰器
"""
from langchain.tools import tool
from typing import Optional
import logging
from datetime import datetime

logger = logging.getLogger(__name__)


def create_schedule_tools(schedule_service, user_id: str):
    """
    创建日程工具集

    Args:
        schedule_service: ScheduleService 实例
        user_id: 当前用户ID

    Returns:
        LangChain 工具列表
    """

    @tool
    async def create_schedule(
        title: str,
        datetime: str,
        description: str = "",
        remind_before: int = 0
    ) -> str:
        """
        创建一个新的日程安排。

        Args:
            title: 日程标题，如：开会、看病、健身
            datetime: 日程时间，支持自然语言，如：明天下午3点、后天上午10点
            description: 日程的详细描述
            remind_before: 提前多少分钟提醒

        Returns:
            操作结果消息
        """
        schedule = await schedule_service.create_schedule(
            user_id=user_id,
            title=title,
            time_str=datetime,
            description=description or None,
            remind_before=remind_before
        )

        if schedule:
            return f"日程创建成功！\n{schedule_service.format_schedule(schedule)}"
        else:
            return "创建日程失败，请检查时间格式是否正确。"

    @tool
    async def query_schedules(date: str = "今天") -> str:
        """
        查询用户在指定日期的日程安排。

        Args:
            date: 查询日期，如：今天、明天、本周、下周

        Returns:
            日程列表消息
        """
        schedules = await schedule_service.list_schedules(
            user_id=user_id,
            date_str=date
        )

        if not schedules:
            return f"{date}没有日程安排。"

        result = f"{date}的日程：\n\n"
        for i, schedule in enumerate(schedules, 1):
            result += f"{i}. {schedule_service.format_schedule(schedule)}\n\n"

        return result.strip()

    @tool
    async def delete_schedule(schedule_id: int) -> str:
        """
        删除指定的日程。

        Args:
            schedule_id: 要删除的日程ID

        Returns:
            操作结果消息
        """
        success = await schedule_service.delete_schedule(schedule_id, user_id)
        if success:
            return f"已删除日程 (ID: {schedule_id})"
        else:
            return f"删除失败，未找到日程或无权操作 (ID: {schedule_id})"

    @tool
    async def update_schedule(
        schedule_id: int,
        title: Optional[str] = None,
        datetime: Optional[str] = None
    ) -> str:
        """
        更新已存在的日程。

        Args:
            schedule_id: 要更新的日程ID
            title: 新的日程标题
            datetime: 新的日程时间

        Returns:
            操作结果消息
        """
        schedule = await schedule_service.update_schedule(
            schedule_id=schedule_id,
            user_id=user_id,
            title=title,
            time_str=datetime
        )

        if schedule:
            return f"日程更新成功！\n{schedule_service.format_schedule(schedule)}"
        else:
            return f"更新失败，未找到日程或无权操作 (ID: {schedule_id})"

    return [create_schedule, query_schedules, delete_schedule, update_schedule]
