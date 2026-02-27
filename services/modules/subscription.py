"""
订阅服务
管理用户的模块订阅状态
"""
import logging
from datetime import datetime
from typing import Optional, List

from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from models.module_subscription import ModuleSubscription
from services.modules.registry import registry

logger = logging.getLogger(__name__)


class SubscriptionService:
    """
    订阅服务

    管理用户对模块的订阅状态
    """

    def __init__(self, db_session: AsyncSession):
        self.db = db_session

    async def get_enabled_modules(self, user_id: str) -> Optional[List[str]]:
        """
        获取用户已启用的模块ID列表

        Args:
            user_id: 用户ID

        Returns:
            已启用的模块ID列表，如果用户没有任何订阅记录则返回 None
        """
        result = await self.db.execute(
            select(ModuleSubscription).where(
                ModuleSubscription.user_id == user_id
            )
        )
        subscriptions = result.scalars().all()

        # 用户没有任何订阅记录
        if not subscriptions:
            return None

        # 返回已启用的模块ID
        return [sub.module_id for sub in subscriptions if sub.enabled]

    async def is_module_enabled(self, user_id: str, module_id: str) -> bool:
        """
        检查用户是否启用了指定模块

        Args:
            user_id: 用户ID
            module_id: 模块ID

        Returns:
            是否启用（没有记录时默认为启用）
        """
        result = await self.db.execute(
            select(ModuleSubscription).where(
                and_(
                    ModuleSubscription.user_id == user_id,
                    ModuleSubscription.module_id == module_id
                )
            )
        )
        subscription = result.scalar_one_or_none()

        # 没有记录，默认启用
        if subscription is None:
            return True

        return subscription.enabled

    async def subscribe(self, user_id: str, module_id: str) -> bool:
        """
        订阅模块

        Args:
            user_id: 用户ID
            module_id: 模块ID

        Returns:
            是否成功
        """
        # 检查模块是否存在
        if module_id not in registry.get_module_ids():
            logger.warning(f"尝试订阅不存在的模块: {module_id}")
            return False

        # 查找现有记录
        result = await self.db.execute(
            select(ModuleSubscription).where(
                and_(
                    ModuleSubscription.user_id == user_id,
                    ModuleSubscription.module_id == module_id
                )
            )
        )
        subscription = result.scalar_one_or_none()

        if subscription:
            # 更新现有记录
            subscription.enabled = True
            subscription.updated_at = datetime.now()
        else:
            # 创建新记录
            subscription = ModuleSubscription(
                user_id=user_id,
                module_id=module_id,
                enabled=True
            )
            self.db.add(subscription)

        await self.db.commit()
        logger.info(f"用户 {user_id} 订阅了模块 {module_id}")
        return True

    async def unsubscribe(self, user_id: str, module_id: str) -> bool:
        """
        取消订阅模块

        Args:
            user_id: 用户ID
            module_id: 模块ID

        Returns:
            是否成功
        """
        # 检查模块是否存在
        if module_id not in registry.get_module_ids():
            logger.warning(f"尝试取消订阅不存在的模块: {module_id}")
            return False

        # 查找现有记录
        result = await self.db.execute(
            select(ModuleSubscription).where(
                and_(
                    ModuleSubscription.user_id == user_id,
                    ModuleSubscription.module_id == module_id
                )
            )
        )
        subscription = result.scalar_one_or_none()

        if subscription:
            # 更新现有记录
            subscription.enabled = False
            subscription.updated_at = datetime.now()
        else:
            # 创建禁用记录
            subscription = ModuleSubscription(
                user_id=user_id,
                module_id=module_id,
                enabled=False
            )
            self.db.add(subscription)

        await self.db.commit()
        logger.info(f"用户 {user_id} 取消订阅了模块 {module_id}")
        return True

    async def subscribe_all(self, user_id: str) -> None:
        """
        订阅所有模块

        Args:
            user_id: 用户ID
        """
        for module_id in registry.get_module_ids():
            await self.subscribe(user_id, module_id)

        logger.info(f"用户 {user_id} 已订阅所有模块")

    async def get_subscription_status(self, user_id: str) -> dict:
        """
        获取用户的订阅状态

        Args:
            user_id: 用户ID

        Returns:
            订阅状态字典 {module_id: enabled}
        """
        result = await self.db.execute(
            select(ModuleSubscription).where(
                ModuleSubscription.user_id == user_id
            )
        )
        subscriptions = result.scalars().all()

        # 构建状态字典
        status = {}
        for module in registry.get_all():
            sub = next(
                (s for s in subscriptions if s.module_id == module.module_id),
                None
            )
            # 没有记录时默认为启用
            status[module.module_id] = sub.enabled if sub else True

        return status
