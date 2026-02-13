"""
提醒服务
使用 APScheduler 实现定时提醒功能
采用动态任务调度：根据用户设置的时间创建对应的定时任务
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
    """提醒服务 - 采用动态任务调度"""

    def __init__(self):
        self.scheduler = AsyncIOScheduler(timezone="Asia/Shanghai")
        self._running_jobs: Set[str] = set()  # 跟踪正在运行的预提醒任务
        self._daily_reminder_jobs: Dict[str, str] = {}  # 跟踪每个用户的每日提醒任务 {user_id: job_id}

    async def start(self):
        """启动调度器"""
        # 确保数据库已初始化
        await init_db()

        # 添加预提醒检查任务 (每分钟检查一次)
        self.scheduler.add_job(
            self.check_pre_schedule_reminders,
            IntervalTrigger(minutes=1),
            id="pre_schedule_check",
            replace_existing=True
        )
        logger.info("已添加日程预提醒检查任务: 每分钟检查")

        # 加载所有用户的每日提醒设置，为每个用户创建定时任务
        await self._load_daily_reminder_jobs()

        self.scheduler.start()
        logger.info("提醒服务已启动")

    async def stop(self):
        """停止调度器"""
        if self.scheduler.running:
            self.scheduler.shutdown(wait=True)
            logger.info("提醒服务已停止")

    async def _load_daily_reminder_jobs(self):
        """
        启动时加载所有用户的每日提醒设置，为每个用户创建定时任务
        """
        try:
            async with AsyncSessionLocal() as db:
                # 获取所有开启了每日提醒的用户设置
                result = await db.execute(
                    select(UserSettings).where(
                        UserSettings.daily_reminder_enabled == True
                    )
                )
                all_settings = result.scalars().all()

                logger.info(f"发现 {len(all_settings)} 个用户开启了每日提醒")

                for user_settings in all_settings:
                    await self._schedule_user_daily_reminder(user_settings)

        except Exception as e:
            logger.error(f"加载每日提醒任务失败: {e}", exc_info=True)

    async def _schedule_user_daily_reminder(self, user_settings: UserSettings):
        """
        为单个用户创建/更新每日提醒定时任务

        Args:
            user_settings: 用户设置对象
        """
        user_id = user_settings.user_id
        reminder_time = user_settings.daily_reminder_time  # 格式: "HH:MM"

        # 解析时间
        try:
            hour, minute = map(int, reminder_time.split(":"))
        except (ValueError, AttributeError):
            logger.warning(f"用户 {user_id} 的提醒时间格式无效: {reminder_time}")
            return

        # 生成唯一的任务ID
        job_id = f"daily_reminder_{user_id}"

        # 如果已有任务，先移除
        if job_id in self._daily_reminder_jobs.values():
            try:
                self.scheduler.remove_job(job_id)
                logger.info(f"已移除用户 {user_id} 的旧定时任务")
            except Exception:
                pass

        # 创建新的定时任务
        try:
            self.scheduler.add_job(
                self._send_user_daily_reminder_wrapper,
                CronTrigger(hour=hour, minute=minute),
                id=job_id,
                args=[user_id],
                replace_existing=True
            )
            self._daily_reminder_jobs[user_id] = job_id
            logger.info(f"已为用户 {user_id} 创建每日提醒任务: {hour:02d}:{minute:02d}")

        except Exception as e:
            logger.error(f"创建定时任务失败 user_id={user_id}: {e}")

    async def _send_user_daily_reminder_wrapper(self, user_id: str):
        """
        发送单个用户每日提醒的包装函数（供调度器调用）
        """
        try:
            async with AsyncSessionLocal() as db:
                # 获取用户设置
                user_settings = await self._get_user_settings(user_id, db)

                # 再次检查是否仍然启用（用户可能在任务触发前关闭了）
                if not user_settings or not user_settings.daily_reminder_enabled:
                    logger.info(f"用户 {user_id} 已关闭每日提醒，跳过发送")
                    return

                await self._send_user_daily_reminder(user_id, db, user_settings)

        except Exception as e:
            logger.error(f"发送每日提醒失败 user_id={user_id}: {e}", exc_info=True)

    async def check_pre_schedule_reminders(self):
        """
        检查并发送日程开始前的提醒
        这个任务需要每分钟检查，因为日程时间是动态的
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
                    if not user_settings or not user_settings.pre_schedule_reminder_enabled:
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

    async def _send_user_daily_reminder(self, user_id: str, db, user_settings=None):
        """发送单个用户的每日日程提醒"""
        # 获取用户设置（如果没有传入）
        if user_settings is None:
            user_settings = await self._get_user_settings(user_id, db)

        if not user_settings or not user_settings.daily_reminder_enabled:
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
            logger.info(f"用户 {user_id} 今天没有日程")
            return

        # 构建提醒消息
        weekday_names = ["周一", "周二", "周三", "周四", "周五", "周六", "周日"]
        today_str = f"{now.month}月{now.day}日 {weekday_names[now.weekday()]}"

        # 根据时间选择问候语
        hour = now.hour
        if hour < 12:
            greeting = "早上好"
        elif hour < 18:
            greeting = "下午好"
        else:
            greeting = "晚上好"

        message = f"📅 {greeting}！今天是 {today_str}\n\n"
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
        更新后会自动重新调度定时任务

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

                # 记录是否需要重新调度
                need_reschedule = False

                if daily_reminder_enabled is not None:
                    settings.daily_reminder_enabled = daily_reminder_enabled
                    need_reschedule = True

                if daily_reminder_time is not None:
                    settings.daily_reminder_time = daily_reminder_time
                    need_reschedule = True

                if pre_schedule_reminder_enabled is not None:
                    settings.pre_schedule_reminder_enabled = pre_schedule_reminder_enabled

                if pre_schedule_reminder_minutes is not None:
                    settings.pre_schedule_reminder_minutes = pre_schedule_reminder_minutes

                settings.updated_at = datetime.utcnow()
                await db.commit()
                await db.refresh(settings)

                logger.info(f"更新用户设置成功: user_id={user_id}")

                # 如果每日提醒设置有变化，重新调度
                if need_reschedule:
                    await self._reschedule_user_daily_reminder(settings)

                return settings

        except Exception as e:
            logger.error(f"更新用户设置失败: {e}", exc_info=True)
            return None

    async def _reschedule_user_daily_reminder(self, user_settings: UserSettings):
        """
        根据用户设置重新调度每日提醒任务

        Args:
            user_settings: 用户设置对象
        """
        user_id = user_settings.user_id
        job_id = f"daily_reminder_{user_id}"

        # 如果用户关闭了每日提醒，移除任务
        if not user_settings.daily_reminder_enabled:
            if user_id in self._daily_reminder_jobs:
                try:
                    self.scheduler.remove_job(job_id)
                    del self._daily_reminder_jobs[user_id]
                    logger.info(f"已移除用户 {user_id} 的每日提醒任务")
                except Exception as e:
                    logger.warning(f"移除任务失败: {e}")
            return

        # 用户开启了每日提醒，创建/更新任务
        await self._schedule_user_daily_reminder(user_settings)

    async def get_user_settings(self, user_id: str) -> Optional[Dict]:
        """获取用户设置"""
        try:
            async with AsyncSessionLocal() as db:
                settings = await self._get_user_settings(user_id, db)
                return settings.to_dict()
        except Exception as e:
            logger.error(f"获取用户设置失败: {e}")
            return None

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

    async def send_test_reminder_now(self, user_id: str = None):
        """
        立即发送测试提醒（用于调试）
        """
        logger.info("开始发送测试提醒...")

        try:
            async with AsyncSessionLocal() as db:
                if user_id:
                    # 发送给指定用户
                    user_ids = [user_id]
                else:
                    # 获取所有有日程的用户
                    result = await db.execute(
                        select(Schedule.user_id).where(
                            Schedule.status == "active"
                        ).distinct()
                    )
                    user_ids = [row[0] for row in result.fetchall()]

                logger.info(f"找到 {len(user_ids)} 个用户")

                for uid in user_ids:
                    try:
                        # 获取该用户的今日日程
                        now = datetime.now()
                        today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
                        today_end = today_start + timedelta(days=1)

                        result = await db.execute(
                            select(Schedule).where(
                                and_(
                                    Schedule.user_id == uid,
                                    Schedule.scheduled_time >= today_start,
                                    Schedule.scheduled_time < today_end,
                                    Schedule.status == "active"
                                )
                            ).order_by(Schedule.scheduled_time)
                        )
                        schedules = result.scalars().all()

                        if schedules:
                            # 构建消息
                            weekday_names = ["周一", "周二", "周三", "周四", "周五", "周六", "周日"]
                            today_str = f"{now.month}月{now.day}日 {weekday_names[now.weekday()]}"

                            message = f"📋 测试提醒 - {today_str}\n\n"
                            message += f"您今天有 {len(schedules)} 个日程：\n\n"

                            for i, schedule in enumerate(schedules, 1):
                                time_str = schedule.scheduled_time.strftime("%H:%M")
                                message += f"{i}. {time_str} - {schedule.title}\n"

                            success = await wechat_push_service.send_text_message(uid, message)
                            logger.info(f"发送给 {uid}: {'成功' if success else '失败'}")

                        await asyncio.sleep(0.5)
                    except Exception as e:
                        logger.error(f"发送测试提醒失败 user_id={uid}: {e}")

        except Exception as e:
            logger.error(f"发送测试提醒失败: {e}", exc_info=True)


# 全局实例
reminder_service = ReminderService()
