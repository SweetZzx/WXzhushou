"""
提醒管理器
统一管理所有模块的提醒服务
"""
import logging
from typing import Dict, List, Optional
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger

from services.reminder.base import BaseReminder

logger = logging.getLogger(__name__)


class ReminderManager:
    """
    提醒管理器

    负责管理和调度所有模块的提醒服务
    """

    def __init__(self):
        self._reminders: Dict[str, BaseReminder] = {}
        self._scheduler: Optional[AsyncIOScheduler] = None
        self._running: bool = False

    def register(self, reminder: BaseReminder):
        """
        注册提醒服务

        Args:
            reminder: 提醒服务实例
        """
        if reminder.reminder_id in self._reminders:
            logger.warning(f"提醒服务 {reminder.reminder_id} 已存在，将被覆盖")

        self._reminders[reminder.reminder_id] = reminder
        logger.info(f"已注册提醒服务: {reminder.reminder_name} (模块: {reminder.module_id})")

    def register_from_modules(self, modules: List):
        """
        从模块列表中注册所有提醒服务

        Args:
            modules: 模块列表
        """
        for module in modules:
            reminders = module.get_reminders()
            for reminder in reminders:
                self.register(reminder)

    def unregister(self, reminder_id: str):
        """注销提醒服务"""
        if reminder_id in self._reminders:
            reminder = self._reminders[reminder_id]
            if self._running:
                import asyncio
                asyncio.create_task(reminder.stop())
            del self._reminders[reminder_id]
            logger.info(f"已注销提醒服务: {reminder_id}")

    def get_reminders_by_module(self, module_id: str) -> List[BaseReminder]:
        """获取指定模块的所有提醒服务"""
        return [
            r for r in self._reminders.values()
            if r.module_id == module_id
        ]

    async def start(self):
        """启动提醒服务"""
        if self._running:
            logger.warning("提醒管理器已在运行")
            return

        # 创建调度器
        self._scheduler = AsyncIOScheduler()

        # 启动所有提醒任务
        for reminder in self._reminders.values():
            try:
                await reminder.start(self._scheduler)
            except Exception as e:
                logger.error(f"启动提醒任务失败 [{reminder.reminder_name}]: {e}")

        # 启动调度器
        self._scheduler.start()
        self._running = True

        logger.info(f"提醒管理器已启动，共 {len(self._reminders)} 个提醒任务")

    async def stop(self):
        """停止提醒服务"""
        if not self._running:
            return

        # 停止所有提醒任务
        for reminder in self._reminders.values():
            try:
                await reminder.stop()
            except Exception as e:
                logger.error(f"停止提醒任务失败 [{reminder.reminder_name}]: {e}")

        # 停止调度器
        if self._scheduler:
            self._scheduler.shutdown(wait=False)
            self._scheduler = None

        self._running = False
        logger.info("提醒管理器已停止")

    def list_reminders(self) -> List[dict]:
        """列出所有提醒服务"""
        return [
            {
                "id": r.reminder_id,
                "name": r.reminder_name,
                "module": r.module_id,
                "config": r.get_schedule_config()
            }
            for r in self._reminders.values()
        ]

    def get_scheduler(self) -> Optional[AsyncIOScheduler]:
        """获取调度器"""
        return self._scheduler


# 全局实例
reminder_manager = ReminderManager()
