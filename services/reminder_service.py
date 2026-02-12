"""
提醒服务
使用 APScheduler 实现定时提醒功能
"""
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger
from sqlalchemy import select, and_
from datetime import datetime, timedelta
from typing import Optional, Dict, Set
import logging
import asyncio

from database.session import AsyncSessionLocal, init_db
from models.schedule import Schedule
from models.user_settings import UserSettings
from services.wechat_push_service import wechat_push_service

logger = logging.getLogger(__name__)


class ReminderService:
    """提醒服务"""

    def __init__(self):
        self.scheduler = AsyncIOScheduler(timezone="Asia/Shanghai")
        self._running_jobs: Set[str] = set()  # 跟踪正在运行的预提醒任务

    async def start(self):
        """启动调度器"""
        # 确保数据库已初始化
        await init_db()

        # 添加每日日程提醒任务 (每日 08:00)
        self.scheduler.add_job(
            self.send_daily_reminders,
            CronTrigger(hour=8, minute=0),
            id="daily_reminder",
            replace_existing=True,
            misfire_grace_time=300
        )
        logger.info("已添加每日日程提醒任务: 08:00")

        # 添加预提醒检查任务 (每分钟检查一次)
        self.scheduler.add_job(
            self.check_pre_schedule_reminders,
            IntervalTrigger(minutes=1),
            id="pre_schedule_check",
            replace_existing=True
        )
        logger.info("已添加日程预提醒检查任务: 每分钟检查")

        self.scheduler.start()
        logger.info("提醒服务已启动")

    async def stop(self):
        """停止调度器"""
        if self.scheduler.running:
            self.scheduler.shutdown(wait=True)
            logger.info("提醒服务已停止")

    async def send_daily_reminders(self):
        """
        发送每日日程提醒
        扫描所有有今日日程的用户，发送提醒
        """
        logger.info("开始执行每日日程提醒...")

        try:
            async with AsyncSessionLocal() as db:
                # 获取今天有日程的所有用户
                now = datetime.now()
                today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
                today_end = today_start + timedelta(days=1)

                # 查询今天有日程的用户
                result = await db.execute(
                    select(Schedule.user_id).where(
                        and_(
                            Schedule.scheduled_time >= today_start,
                            Schedule.scheduled_time < today_end,
                            Schedule.status == "active"
                        )
                    ).distinct()
                )
                user_ids = [row[0] for row in result.fetchall()]

                logger.info(f"找到 {len(user_ids)} 个用户有今日日程")

                # 给每个用户发送提醒
                for user_id in user_ids:
                    try:
                        await self._send_user_daily_reminder(user_id, db)
                        # 避免请求过快
                        await asyncio.sleep(0.5)
                    except Exception as e:
                        logger.error(f"发送每日提醒失败 user_id={user_id}: {e}")

        except Exception as e:
            logger.error(f"执行每日提醒任务失败: {e}", exc_info=True)

    async def _send_user_daily_reminder(self, user_id: str, db):
        """发送单个用户的每日日程提醒"""
        # 获取用户设置
        user_settings = await self._get_user_settings(user_id, db)
        if not user_settings.daily_reminder_enabled:
            logger.info(f"用户 {user_id} 已关闭每日提醒")
            return

        # 获取今日日程
        now = datetime.now()
        today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        today_end = today_start + timedelta(days=1)

        result = await db.execute(
            select(Schedule).where(
                and_(
                    Schedule.user_id == user_id,
                    Schedule.scheduled_time >= today_start,
                    Schedule.scheduled_time < today_end,
                    Schedule.status == "active"
                )
            ).order_by(Schedule.scheduled_time)
        )
        schedules = result.scalars().all()

        if not schedules:
            return

        # 构建提醒消息
        weekday_names = ["周一", "周二", "周三", "周四", "周五", "周六", "周日"]
        today_str = f"{now.month}月{now.day}日 {weekday_names[now.weekday()]}"

        message = f"📅 早上好！今天是 {today_str}\n\n"
        message += f"您今天有 {len(schedules)} 个日程安排：\n\n"

        for i, schedule in enumerate(schedules, 1):
            time_str = schedule.scheduled_time.strftime("%H:%M")
            message += f"{i}. {time_str} - {schedule.title}\n"

        message += "\n祝您今天愉快！🎉"

        # 发送消息
        success = await wechat_push_service.send_text_message(user_id, message)
        if success:
            logger.info(f"已发送每日提醒给用户 {user_id}")
        else:
            logger.warning(f"发送每日提醒失败 user_id={user_id}")

    async def check_pre_schedule_reminders(self):
        """
        检查并发送日程开始前的提醒
        """
        now = datetime.now()

        # 查找需要提醒的日程（10分钟内开始，且未发送过提醒）
        check_start = now + timedelta(minutes=1)  # 1分钟后
        check_end = now + timedelta(minutes=11)   # 11分钟后

        try:
            async with AsyncSessionLocal() as db:
                # 查找即将开始的日程
                result = await db.execute(
                    select(Schedule).where(
                        and_(
                            Schedule.scheduled_time >= check_start,
                            Schedule.scheduled_time < check_end,
                            Schedule.status == "active"
                        )
                    )
                )
                schedules = result.scalars().all()

                for schedule in schedules:
                    job_key = f"pre_remind_{schedule.id}_{schedule.scheduled_time.strftime('%Y%m%d%H%M')}"

                    # 避免重复发送
                    if job_key in self._running_jobs:
                        continue

                    # 检查用户是否开启预提醒
                    user_settings = await self._get_user_settings(schedule.user_id, db)
                    if not user_settings.pre_schedule_reminder_enabled:
                        continue

                    # 计算提醒时间
                    minutes_left = int((schedule.scheduled_time - now).total_seconds() / 60)

                    # 只在接近用户设置的提前时间时发送
                    if minutes_left <= user_settings.pre_schedule_reminder_minutes:
                        self._running_jobs.add(job_key)
                        try:
                            await self._send_pre_schedule_reminder(schedule, minutes_left)
                        finally:
                            # 5分钟后清理，避免内存泄漏
                            asyncio.get_event_loop().call_later(
                                300,
                                lambda: self._running_jobs.discard(job_key)
                            )

        except Exception as e:
            logger.error(f"检查预提醒任务失败: {e}", exc_info=True)

    async def _send_pre_schedule_reminder(self, schedule: Schedule, minutes_left: int):
        """发送日程开始前提醒"""
        time_str = schedule.scheduled_time.strftime("%H:%M")

        message = f"⏰ 日程提醒\n\n"
        message += f"📅 {schedule.title}\n"
        message += f"🕐 {time_str} 开始\n"
        message += f"⏱️ 还有 {minutes_left} 分钟\n"

        if schedule.description:
            message += f"\n📝 {schedule.description}"

        success = await wechat_push_service.send_text_message(schedule.user_id, message)
        if success:
            logger.info(f"已发送预提醒给用户 {schedule.user_id}: {schedule.title}")
        else:
            logger.warning(f"发送预提醒失败 user_id={schedule.user_id}")

    async def _get_user_settings(self, user_id: str, db) -> UserSettings:
        """获取用户设置，不存在则创建默认设置"""
        result = await db.execute(
            select(UserSettings).where(UserSettings.user_id == user_id)
        )
        settings = result.scalar_one_or_none()

        if not settings:
            settings = UserSettings(user_id=user_id)
            db.add(settings)
            await db.commit()
            await db.refresh(settings)

        return settings

    async def update_user_settings(
        self,
        user_id: str,
        daily_reminder_enabled: Optional[bool] = None,
        daily_reminder_time: Optional[str] = None,
        pre_schedule_reminder_enabled: Optional[bool] = None,
        pre_schedule_reminder_minutes: Optional[int] = None
    ) -> Optional[UserSettings]:
        """
        更新用户提醒设置

        Args:
            user_id: 用户ID
            daily_reminder_enabled: 是否启用每日提醒
            daily_reminder_time: 每日提醒时间 (HH:MM)
            pre_schedule_reminder_enabled: 是否启用日程前提醒
            pre_schedule_reminder_minutes: 日程前提前多少分钟提醒

        Returns:
            更新后的用户设置
        """
        try:
            async with AsyncSessionLocal() as db:
                settings = await self._get_user_settings(user_id, db)

                if daily_reminder_enabled is not None:
                    settings.daily_reminder_enabled = daily_reminder_enabled
                if daily_reminder_time is not None:
                    settings.daily_reminder_time = daily_reminder_time
                if pre_schedule_reminder_enabled is not None:
                    settings.pre_schedule_reminder_enabled = pre_schedule_reminder_enabled
                if pre_schedule_reminder_minutes is not None:
                    settings.pre_schedule_reminder_minutes = pre_schedule_reminder_minutes

                settings.updated_at = datetime.utcnow()
                await db.commit()
                await db.refresh(settings)

                logger.info(f"更新用户设置成功: user_id={user_id}")
                return settings

        except Exception as e:
            logger.error(f"更新用户设置失败: {e}", exc_info=True)
            return None

    async def get_user_settings(self, user_id: str) -> Optional[Dict]:
        """获取用户设置"""
        try:
            async with AsyncSessionLocal() as db:
                settings = await self._get_user_settings(user_id, db)
                return settings.to_dict()
        except Exception as e:
            logger.error(f"获取用户设置失败: {e}")
            return None

    def reschedule_daily_reminder(self, hour: int, minute: int):
        """
        重新设置每日提醒时间

        Args:
            hour: 小时
            minute: 分钟
        """
        self.scheduler.remove_job("daily_reminder")
        self.scheduler.add_job(
            self.send_daily_reminders,
            CronTrigger(hour=hour, minute=minute),
            id="daily_reminder",
            replace_existing=True
        )
        logger.info(f"每日提醒时间已更新为 {hour:02d}:{minute:02d}")

    async def test_push(self, user_id: str, message: str = "这是一条测试消息") -> bool:
        """
        测试推送功能

        Args:
            user_id: 用户ID
            message: 测试消息内容

        Returns:
            是否成功
        """
        logger.info(f"开始测试推送: user_id={user_id}")
        success = await wechat_push_service.send_text_message(user_id, message)
        if success:
            logger.info(f"测试推送成功: user_id={user_id}")
        else:
            logger.error(f"测试推送失败: user_id={user_id}")
        return success

    async def send_test_reminder_now(self):
        """
        立即发送测试提醒（用于调试）
        向所有有日程的用户发送明天的日程提醒
        """
        logger.info("开始发送测试提醒...")

        try:
            async with AsyncSessionLocal() as db:
                # 获取所有有日程的用户
                result = await db.execute(
                    select(Schedule.user_id).where(
                        Schedule.status == "active"
                    ).distinct()
                )
                user_ids = [row[0] for row in result.fetchall()]

                logger.info(f"找到 {len(user_ids)} 个用户有日程")

                for user_id in user_ids:
                    try:
                        # 获取该用户的所有日程
                        result = await db.execute(
                            select(Schedule).where(
                                and_(
                                    Schedule.user_id == user_id,
                                    Schedule.status == "active"
                                )
                            ).order_by(Schedule.scheduled_time)
                        )
                        schedules = result.scalars().all()

                        if schedules:
                            # 构建消息
                            message = f"📋 日程提醒测试\n\n"
                            message += f"您有 {len(schedules)} 个日程：\n\n"

                            for i, schedule in enumerate(schedules, 1):
                                time_str = schedule.scheduled_time.strftime("%m-%d %H:%M")
                                message += f"{i}. {time_str} - {schedule.title}\n"

                            success = await wechat_push_service.send_text_message(user_id, message)
                            logger.info(f"发送给 {user_id}: {'成功' if success else '失败'}")

                        await asyncio.sleep(0.5)
                    except Exception as e:
                        logger.error(f"发送测试提醒失败 user_id={user_id}: {e}")

        except Exception as e:
            logger.error(f"发送测试提醒失败: {e}", exc_info=True)


# 全局实例
reminder_service = ReminderService()
