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
        【日程管理工具】当用户明确想要创建、记录、安排或计划某个事项时使用此工具。

        触发条件示例：
        - "帮我记一下明天下午3点开会"
        - "提醒我周五去医院"
        - "安排一个下周的会议"
        - "我要添加一个日程"

        不要在以下情况使用：
        - 用户只是提到某个时间（如"现在几点了"）
        - 用户在询问一般性问题

        Args:
            title: 日程标题，如：开会、看病、健身
            datetime: 日程时间，支持自然语言，如：明天下午3点、后天上午10点
            description: 日程的详细描述
            remind_before: 提前多少分钟提醒
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
        【日程管理工具】当用户想要查看或了解已有的日程安排时使用此工具。

        触发条件示例：
        - "明天有什么安排？"
        - "查看我的日程"
        - "这周有事吗？"
        - "我有哪些日程？"

        不要在以下情况使用：
        - 用户只是提到日期（如"今天是几号"）

        Args:
            date: 查询日期，如：今天、明天、本周、下周
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
        【日程管理工具】当用户明确想要取消或删除已有的日程时使用此工具。

        触发条件示例：
        - "取消明天的会议"
        - "删除日程1"
        - "把这个日程删掉"

        Args:
            schedule_id: 要删除的日程ID
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
        【日程管理工具】当用户想要修改或更改已有的日程时使用此工具。

        触发条件示例：
        - "把那个会议改到后天"
        - "修改日程1的时间"
        - "更新一下我的安排"

        Args:
            schedule_id: 要更新的日程ID
            title: 新的日程标题
            datetime: 新的日程时间
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
