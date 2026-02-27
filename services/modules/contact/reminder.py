"""
联系人生日提醒服务
提前7天和当天发送生日提醒
"""
import logging
from datetime import date, timedelta
from typing import List

from services.reminder.base import BaseReminder
from database import db_session
from services.wechat_push_service import wechat_push_service

logger = logging.getLogger(__name__)


class BirthdayReminder(BaseReminder):
    """生日提醒"""

    reminder_id = "contact_birthday"
    reminder_name = "联系人生日提醒"
    module_id = "contact"

    async def check(self):
        """检查并发送生日提醒"""
        from services.modules.contact.service import ContactService
        from services.modules.subscription import SubscriptionService

        async with db_session.AsyncSessionLocal() as db:
            contact_service = ContactService(db)
            subscription_service = SubscriptionService(db)

            # 获取未来7天内过生日的联系人
            upcoming = await contact_service.get_upcoming_birthdays(days=7)

            logger.info(f"检查生日提醒: 发现 {len(upcoming)} 个即将过生日的联系人")

            for contact in upcoming:
                user_id = contact["user_id"]
                name = contact["name"]
                days_until = contact["days_until"]

                # 检查用户是否订阅了联系人模块
                if not await subscription_service.is_module_enabled(user_id, "contact"):
                    continue

                # 发送提醒
                if days_until == 0:
                    message = f"今天是 {name} 的生日！\n\n别忘了送上祝福~"
                else:
                    message = f"{name} 的生日还有 {days_until} 天就到了\n\n生日: {contact['birthday']}\n记得准备礼物哦~"

                success = await wechat_push_service.send_text_message(user_id, message)
                if success:
                    logger.info(f"已发送生日提醒: user={user_id}, name={name}, days={days_until}")

    def get_schedule_config(self) -> dict:
        """每天 8:00 执行"""
        return {
            "trigger": "cron",
            "hour": 8,
            "minute": 0
        }


# 导出实例
birthday_reminder = BirthdayReminder()
