"""
日程模块实现
"""
import logging
from datetime import datetime
from typing import Type

from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from services.modules.base import BaseModule
from services.chat_with_action import ScheduleAction  # 使用统一的 Action 定义
from services.schedule_service import ScheduleService
from services.reminder_service import reminder_service
from utils.time_parser import parse_time

logger = logging.getLogger(__name__)

WEEKDAYS = ["星期一", "星期二", "星期三", "星期四", "星期五", "星期六", "星期日"]

# 日程模块的 SYSTEM_PROMPT 片段
SCHEDULE_PROMPT = """
【日程意图判断】
消息包含「时间 + 事件」时创建日程：
- "下周五看电影" → type: "create", title: "看电影", time: "下周五"
- "明天开会" → type: "create", title: "开会", time: "明天"
- "明天有什么安排" → type: "query", date: "明天"
- "所有日程" / "全部日程" → type: "query", date: "所有"
"""


class ScheduleModule(BaseModule):
    """日程管理模块"""

    module_id: str = "schedule"
    module_name: str = "日程管理"
    module_description: str = "管理你的日程安排，支持创建、查询、修改和删除日程"

    @property
    def action_model(self) -> Type[BaseModel]:
        return ScheduleAction

    async def execute(
        self,
        action: BaseModel,
        user_id: str,
        db_session: AsyncSession
    ) -> str:
        """执行日程操作"""
        if not isinstance(action, ScheduleAction):
            return "日程操作格式错误"

        action_type = action.type

        if action_type == "create":
            return await self._handle_create(action, user_id, db_session)
        elif action_type == "query":
            return await self._handle_query(action, user_id, db_session)
        elif action_type == "update":
            return await self._handle_update(action, user_id, db_session)
        elif action_type == "delete":
            return await self._handle_delete(action, user_id, db_session)
        elif action_type == "settings":
            return await self._handle_settings(user_id)
        elif action_type == "update_settings":
            return await self._handle_update_settings(action, user_id)
        else:
            return "未知的日程操作"

    def get_prompt_section(self) -> str:
        return SCHEDULE_PROMPT

    async def _handle_create(self, action: ScheduleAction, user_id: str, db_session) -> str:
        """创建日程"""
        schedule_service = ScheduleService(db_session)

        title = action.title or "未命名日程"
        time_desc = action.time or "今天"

        parsed_time = parse_time(time_desc, datetime.now())
        if not parsed_time:
            return f"没有太理解时间「{time_desc}」，能再说具体点吗？比如「明天下午3点」"

        schedule = await schedule_service.create_schedule(
            user_id=user_id,
            title=title,
            time_str=parsed_time.strftime("%Y-%m-%d %H:%M"),
            description=None
        )

        if schedule:
            time_str = schedule.scheduled_time.strftime("%m月%d日 %H:%M")
            weekday = WEEKDAYS[schedule.scheduled_time.weekday()]

            if schedule.scheduled_time.hour == 0 and schedule.scheduled_time.minute == 0:
                time_str = schedule.scheduled_time.strftime("%m月%d日")

            return f"好的，已帮你记下了！\n\n{schedule.title}\n时间: {time_str} ({weekday})"

        return "创建失败，请稍后重试"

    async def _handle_query(self, action: ScheduleAction, user_id: str, db_session) -> str:
        """查询日程"""
        schedule_service = ScheduleService(db_session)

        date_str = action.date or ""
        query_all = not date_str or "所有" in date_str or "全部" in date_str

        if query_all:
            schedules = await schedule_service.list_schedules(user_id=user_id, date_str=None)
            date_display = "所有"
        else:
            schedules = await schedule_service.list_schedules(user_id=user_id, date_str=date_str)
            date_display = date_str

        if not schedules:
            return f"{'目前还没有日程安排' if query_all else date_display + '没有日程安排'}"

        if len(schedules) == 1:
            s = schedules[0]
            time_str = s.scheduled_time.strftime("%m月%d日 %H:%M")
            weekday = WEEKDAYS[s.scheduled_time.weekday()]
            return f"{'目前' if query_all else date_display}有1个日程：\n\n{s.title}\n时间: {time_str} ({weekday})"

        result = f"{'你记录的所有日程' if query_all else date_display + '的日程'}（共{len(schedules)}个）：\n"
        for i, s in enumerate(schedules, 1):
            time_str = s.scheduled_time.strftime("%m月%d日 %H:%M")
            weekday = WEEKDAYS[s.scheduled_time.weekday()]
            result += f"\n{i}. {s.title} - {time_str} ({weekday})"

        return result

    async def _handle_update(self, action: ScheduleAction, user_id: str, db_session) -> str:
        """修改日程"""
        schedule_service = ScheduleService(db_session)

        target_id = None

        if action.target:
            try:
                target_id = int(action.target)
            except ValueError:
                schedules = await schedule_service.find_schedules_by_keyword(
                    user_id=user_id,
                    keyword=action.target
                )
                if len(schedules) == 1:
                    target_id = schedules[0].id
                elif len(schedules) > 1:
                    return f"找到 {len(schedules)} 个匹配的日程，请告诉我具体是哪个"

        if not target_id:
            return "没找到要修改的日程，能告诉我具体是哪个吗？"

        new_time_str = None
        if action.time:
            parsed = parse_time(action.time, datetime.now())
            if parsed:
                new_time_str = parsed.strftime("%Y-%m-%d %H:%M")

        schedule = await schedule_service.update_schedule(
            schedule_id=target_id,
            user_id=user_id,
            title=action.title,
            time_str=new_time_str
        )

        if schedule:
            time_str = schedule.scheduled_time.strftime("%m月%d日 %H:%M")
            weekday = WEEKDAYS[s.scheduled_time.weekday()]
            return f"已更新：{schedule.title}\n时间: {time_str} ({weekday})"

        return "更新失败，未找到日程"

    async def _handle_delete(self, action: ScheduleAction, user_id: str, db_session) -> str:
        """删除日程"""
        schedule_service = ScheduleService(db_session)

        target_id = None

        if action.target:
            try:
                target_id = int(action.target)
            except ValueError:
                schedules = await schedule_service.find_schedules_by_keyword(
                    user_id=user_id,
                    keyword=action.target
                )
                if len(schedules) == 1:
                    target_id = schedules[0].id

        if not target_id:
            return "没找到要删除的日程"

        success = await schedule_service.delete_schedule(target_id, user_id)

        if success:
            return "已删除日程"

        return "删除失败"

    async def _handle_settings(self, user_id: str) -> str:
        """查看提醒设置"""
        settings = await reminder_service.get_user_settings(user_id)

        if settings:
            daily_status = "已开启" if settings["daily_reminder_enabled"] else "已关闭"
            pre_status = "已开启" if settings["pre_schedule_reminder_enabled"] else "已关闭"

            return (
                f"你的提醒设置：\n\n"
                f"每日日程提醒：{daily_status}\n"
                f"  提醒时间：{settings['daily_reminder_time']}\n\n"
                f"日程开始前提醒：{pre_status}\n"
                f"  提前 {settings['pre_schedule_reminder_minutes']} 分钟提醒"
            )

        return "获取设置失败，请稍后重试"

    async def _handle_update_settings(self, action: ScheduleAction, user_id: str) -> str:
        """修改提醒设置"""
        settings = await reminder_service.update_user_settings(
            user_id=user_id,
            daily_reminder_enabled=action.daily_reminder_enabled,
            daily_reminder_time=action.daily_reminder_time,
            pre_schedule_reminder_enabled=action.pre_reminder_enabled,
            pre_schedule_reminder_minutes=action.pre_reminder_minutes
        )

        if settings:
            daily_status = "已开启" if settings.daily_reminder_enabled else "已关闭"
            pre_status = "已开启" if settings.pre_schedule_reminder_enabled else "已关闭"

            return (
                f"设置已更新！\n\n"
                f"每日日程提醒：{daily_status}\n"
                f"  提醒时间：{settings.daily_reminder_time}\n\n"
                f"日程开始前提醒：{pre_status}\n"
                f"  提前 {settings.pre_schedule_reminder_minutes} 分钟提醒"
            )

        return "更新设置失败，请稍后重试"


# 创建模块实例并注册
schedule_module = ScheduleModule()
