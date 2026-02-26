"""
日程执行器
根据 LLM 提取的结构化数据执行日程操作
"""
import logging
from datetime import datetime
from typing import Optional

from services.schedule_service import ScheduleService
from services.reminder_service import reminder_service
from services.chat_with_action import chat_service, AIOutput, ScheduleAction
from utils.time_parser import parse_time

logger = logging.getLogger(__name__)

WEEKDAYS = ["星期一", "星期二", "星期三", "星期四", "星期五", "星期六", "星期日"]


class ScheduleExecutor:
    """日程执行器"""

    def __init__(self):
        self._last_schedule_id = {}  # user_id -> last created schedule id

    async def process(
        self,
        message: str,
        user_id: str,
        db_session,
        history: list = None
    ) -> tuple[str, Optional[AIOutput]]:
        """
        处理消息并执行操作

        Returns:
            (response, ai_output) - 回复内容 和 AI输出对象
        """
        # 1. 调用 LLM 获取回复和意图
        ai_output = await chat_service.process(message, history)

        # 2. 如果有日程操作，执行并返回模板回复
        if ai_output.action:
            response = await self._execute_action(
                ai_output.action,
                user_id,
                db_session,
                ai_output.reply
            )
        else:
            response = ai_output.reply

        return response, ai_output

    async def execute(
        self,
        action: ScheduleAction,
        user_id: str,
        db_session,
        ai_reply: str
    ) -> str:
        """
        执行日程操作（供外部调用）

        Args:
            action: 日程操作
            user_id: 用户ID
            db_session: 数据库会话
            ai_reply: AI 的原始回复

        Returns:
            执行结果
        """
        return await self._execute_action(action, user_id, db_session, ai_reply)

    async def _execute_action(
        self,
        action: ScheduleAction,
        user_id: str,
        db_session,
        ai_reply: str
    ) -> str:
        """执行日程操作"""

        if action.type == "create":
            return await self._handle_create(action, user_id, db_session)

        elif action.type == "query":
            return await self._handle_query(action, user_id, db_session)

        elif action.type == "update":
            return await self._handle_update(action, user_id, db_session)

        elif action.type == "delete":
            return await self._handle_delete(action, user_id, db_session)

        elif action.type == "settings":
            return await self._handle_settings(user_id)

        elif action.type == "update_settings":
            return await self._handle_update_settings(action, user_id)

        else:
            return ai_reply  # 未知操作，返回 AI 回复

    async def _handle_create(self, action: ScheduleAction, user_id: str, db_session) -> str:
        """创建日程"""
        schedule_service = ScheduleService(db_session)

        # 解析时间
        title = action.title or "未命名日程"
        time_desc = action.time or "今天"

        parsed_time = parse_time(time_desc, datetime.now())
        if not parsed_time:
            # 时间解析失败，尝试只解析日期
            return f"🕐 没太理解时间「{time_desc}」，能再说具体点吗？比如「明天下午3点」"

        # 创建日程
        schedule = await schedule_service.create_schedule(
            user_id=user_id,
            title=title,
            time_str=parsed_time.strftime("%Y-%m-%d %H:%M"),
            description=None
        )

        if schedule:
            self._last_schedule_id[user_id] = schedule.id
            time_str = schedule.scheduled_time.strftime("%m月%d日 %H:%M")
            weekday = WEEKDAYS[schedule.scheduled_time.weekday()]

            # 如果没有具体时间（默认00:00），显示不同格式
            if schedule.scheduled_time.hour == 0 and schedule.scheduled_time.minute == 0:
                time_str = schedule.scheduled_time.strftime("%m月%d日")

            return f"✅ 好的，已帮你记下了！\n\n📌 {schedule.title}\n⏰ {time_str} ({weekday})"

        return "❌ 创建失败，请稍后重试"

    async def _handle_query(self, action: ScheduleAction, user_id: str, db_session) -> str:
        """查询日程"""
        schedule_service = ScheduleService(db_session)
        date_str = action.date or "今天"

        schedules = await schedule_service.list_schedules(user_id=user_id, date_str=date_str)

        if not schedules:
            return f"📭 {date_str}没有日程安排"

        if len(schedules) == 1:
            s = schedules[0]
            time_str = s.scheduled_time.strftime("%m月%d日 %H:%M")
            weekday = WEEKDAYS[s.scheduled_time.weekday()]
            return f"📅 {date_str}有1个日程：\n\n📌 {s.title}\n⏰ {time_str} ({weekday})"

        result = f"📅 {date_str}的日程（共{len(schedules)}个）：\n"
        for i, s in enumerate(schedules, 1):
            time_str = s.scheduled_time.strftime("%H:%M")
            result += f"\n{i}. {s.title} - {time_str}"

        return result

    async def _handle_update(self, action: ScheduleAction, user_id: str, db_session) -> str:
        """修改日程"""
        schedule_service = ScheduleService(db_session)

        # 确定目标 ID
        target_id = None

        if action.target:
            # 尝试解析为 ID
            try:
                target_id = int(action.target)
            except ValueError:
                # 按关键词搜索
                schedules = await schedule_service.find_schedules_by_keyword(
                    user_id=user_id,
                    keyword=action.target
                )
                if len(schedules) == 1:
                    target_id = schedules[0].id
                elif len(schedules) > 1:
                    return f"🔍 找到 {len(schedules)} 个匹配的日程，请告诉我具体是哪个（回复ID）"
        else:
            # 使用最近创建的日程
            target_id = self._last_schedule_id.get(user_id)

        if not target_id:
            return "❓ 没找到要修改的日程，能告诉我具体是哪个吗？"

        # 解析新时间
        new_time_str = None
        if action.time:
            parsed = parse_time(action.time, datetime.now())
            if parsed:
                new_time_str = parsed.strftime("%Y-%m-%d %H:%M")

        # 执行更新
        schedule = await schedule_service.update_schedule(
            schedule_id=target_id,
            user_id=user_id,
            title=action.title,
            time_str=new_time_str
        )

        if schedule:
            time_str = schedule.scheduled_time.strftime("%m月%d日 %H:%M")
            weekday = WEEKDAYS[schedule.scheduled_time.weekday()]
            return f"✅ 已更新：{schedule.title}\n⏰ {time_str} ({weekday})"

        return "❌ 更新失败，未找到日程"

    async def _handle_delete(self, action: ScheduleAction, user_id: str, db_session) -> str:
        """删除日程"""
        schedule_service = ScheduleService(db_session)

        # 确定目标 ID
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
                    return f"🔍 找到 {len(schedules)} 个匹配，请告诉我ID"

        if not target_id:
            return "❓ 没找到要删除的日程"

        success = await schedule_service.delete_schedule(target_id, user_id)

        if success:
            return f"✅ 已删除日程"

        return "❌ 删除失败"

    async def _handle_settings(self, user_id: str) -> str:
        """查看提醒设置"""
        settings = await reminder_service.get_user_settings(user_id)

        if settings:
            daily_status = "✅ 已开启" if settings["daily_reminder_enabled"] else "❌ 已关闭"
            pre_status = "✅ 已开启" if settings["pre_schedule_reminder_enabled"] else "❌ 已关闭"

            return (
                f"⏰ 你的提醒设置：\n\n"
                f"📅 每日日程提醒：{daily_status}\n"
                f"   └─ 提醒时间：{settings['daily_reminder_time']}\n\n"
                f"🔔 日程开始前提醒：{pre_status}\n"
                f"   └─ 提前 {settings['pre_schedule_reminder_minutes']} 分钟提醒"
            )

        return "❌ 获取设置失败，请稍后重试"

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
            daily_status = "✅ 已开启" if settings.daily_reminder_enabled else "❌ 已关闭"
            pre_status = "✅ 已开启" if settings.pre_schedule_reminder_enabled else "❌ 已关闭"

            return (
                f"✅ 设置已更新！\n\n"
                f"📅 每日日程提醒：{daily_status}\n"
                f"   └─ 提醒时间：{settings.daily_reminder_time}\n\n"
                f"🔔 日程开始前提醒：{pre_status}\n"
                f"   └─ 提前 {settings.pre_schedule_reminder_minutes} 分钟提醒"
            )

        return "❌ 更新设置失败，请稍后重试"


# 全局实例
schedule_executor = ScheduleExecutor()
