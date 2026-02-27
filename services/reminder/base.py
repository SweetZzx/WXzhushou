"""
提醒服务基类
所有模块的提醒功能都继承此类
"""
from abc import ABC, abstractmethod
from typing import Optional
import logging

logger = logging.getLogger(__name__)


class BaseReminder(ABC):
    """
    提醒服务基类

    每个模块可以有自己的提醒服务，继承此类实现具体逻辑
    """

    # 子类必须指定
    reminder_id: str = ""           # 提醒ID（唯一标识）
    reminder_name: str = ""         # 提醒名称
    module_id: str = ""             # 关联的模块ID

    def __init__(self):
        self._scheduler = None
        self._job = None

    @abstractmethod
    async def check(self):
        """
        检查并发送提醒

        由子类实现具体逻辑：
        1. 查询需要提醒的数据
        2. 检查用户是否订阅了对应模块
        3. 发送提醒
        """
        pass

    @abstractmethod
    def get_schedule_config(self) -> dict:
        """
        获取调度配置

        Returns:
            调度配置字典，例如：
            - 间隔执行: {"trigger": "interval", "minutes": 30}
            - 定时执行: {"trigger": "cron", "hour": 8, "minute": 0}
        """
        pass

    async def should_remind_user(self, user_id: str, db_session) -> bool:
        """
        检查用户是否应该收到此提醒

        Args:
            user_id: 用户ID
            db_session: 数据库会话

        Returns:
            是否应该发送提醒
        """
        from services.modules.subscription import SubscriptionService

        subscription_service = SubscriptionService(db_session)
        return await subscription_service.is_module_enabled(user_id, self.module_id)

    async def start(self, scheduler):
        """
        启动提醒任务

        Args:
            scheduler: APScheduler 调度器
        """
        if self._job:
            logger.warning(f"提醒任务 {self.reminder_id} 已在运行")
            return

        self._scheduler = scheduler
        config = self.get_schedule_config()

        self._job = scheduler.add_job(
            self._run_check,
            **config,
            id=f"reminder_{self.reminder_id}",
            name=self.reminder_name,
            replace_existing=True
        )

        logger.info(f"提醒任务已启动: {self.reminder_name}")

    async def stop(self):
        """停止提醒任务"""
        if self._job:
            self._job.remove()
            self._job = None
            logger.info(f"提醒任务已停止: {self.reminder_name}")

    async def _run_check(self):
        """执行检查（包装器，处理异常）"""
        try:
            logger.debug(f"执行提醒检查: {self.reminder_name}")
            await self.check()
        except Exception as e:
            logger.error(f"提醒检查失败 [{self.reminder_name}]: {e}", exc_info=True)

    def __repr__(self) -> str:
        return f"<Reminder {self.reminder_id}: {self.reminder_name}>"
