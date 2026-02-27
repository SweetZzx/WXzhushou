"""
日程提醒服务
每日日程提醒 + 日程开始前提醒
"""
import logging
from datetime import datetime, date
from typing import List

from services.reminder.base import BaseReminder
from database import db_session
from services.wechat_push_service import wechat_push_service

logger = logging.getLogger(__name__)


class DailyScheduleReminder(BaseReminder):
    """每日日程提醒"""

    reminder_id = "schedule_daily"
    reminder_name = "每日日程提醒"
    module_id = "schedule"

    async def check(self):
        """检查并发送每日日程提醒"""
        from services.modules.schedule.service import ScheduleService
        from services.modules.subscription import SubscriptionService

        async with db_session.AsyncSessionLocal() as db:
            # 获取所有订阅了日程模块的用户
            subscription_service = SubscriptionService(db)
            schedule_service = ScheduleService(db)

            # 获取今日日期
            today = date.today()
            date_str = f"{today.month}月{today.day}日"

            # 遍历所有用户（这里简化处理，实际应该只处理订阅用户）
            # TODO: 需要实现获取所有订阅用户的方法

            logger.info(f"执行每日日程提醒检查: {date_str}")

    def get_schedule_config(self) -> dict:
        """每天 8:00 执行"""
        return {
            "trigger": "cron",
            "hour": 8,
            "minute": 0
        }

    async def send_user_daily_reminder(self, user_id: str):
        """发送单个用户的每日提醒"""
        from services.modules.schedule.service import ScheduleService
        from services.modules.subscription import SubscriptionService

        async with db_session.AsyncSessionLocal() as db:
            # 检查用户是否订阅了日程模块
            subscription_service = SubscriptionService(db)
            if not await subscription_service.is_module_enabled(user_id, "schedule"):
                return

            # 获取今日日程
            schedule_service = ScheduleService(db)
            schedules = await schedule_service.list_schedules(user_id, "今天")

            if not schedules:
                return

            # 构建提醒消息
            today = date.today()
            date_str = f"{today.month}月{today.day}日"

            if len(schedules) == 1:
                s = schedules[0]
                time_str = s.scheduled_time.strftime("%H:%M")
                message = f"早上好！今天有1个日程：\n\n{s.title}\n时间: {time_str}"
            else:
                message = f"早上好！今天有{len(schedules)}个日程：\n"
                for i, s in enumerate(schedules, 1):
                    time_str = s.scheduled_time.strftime("%H:%M")
                    message += f"\n{i}. {s.title} - {time_str}"

            # 发送消息
            await wechat_push_service.send_text_message(user_id, message)
            logger.info(f"已发送每日日程提醒: user={user_id}")


class PreScheduleReminder(BaseReminder):
    """日程开始前提醒"""

    reminder_id = "schedule_pre"
    reminder_name = "日程开始前提醒"
    module_id = "schedule"

    async def check(self):
        """检查即将开始的日程"""
        from services.modules.schedule.service import ScheduleService
        from services.modules.subscription import SubscriptionService

        async with db_session.AsyncSessionLocal() as db:
            schedule_service = ScheduleService(db)
            subscription_service = SubscriptionService(db)

            # TODO: 实现查询即将开始的日程逻辑
            logger.debug("执行日程开始前提醒检查")

    def get_schedule_config(self) -> dict:
        """每 5 分钟检查一次"""
        return {
            "trigger": "interval",
            "minutes": 5
        }


# 导出实例
daily_schedule_reminder = DailyScheduleReminder()
pre_schedule_reminder = PreScheduleReminder()
