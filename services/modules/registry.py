"""
模块注册表
管理所有可用的模块
"""
import logging
from typing import Optional, List, Dict, TYPE_CHECKING

from services.modules.base import BaseModule

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)


class ModuleRegistry:
    """
    模块注册表

    使用类方法实现全局单例模式
    """

    _modules: Dict[str, BaseModule] = {}
    _initialized: bool = False

    @classmethod
    def register(cls, module: BaseModule) -> None:
        """
        注册模块

        Args:
            module: 模块实例
        """
        if module.module_id in cls._modules:
            logger.warning(f"模块 {module.module_id} 已存在，将被覆盖")

        cls._modules[module.module_id] = module
        logger.info(f"已注册模块: {module.module_id} ({module.module_name})")

    @classmethod
    def get(cls, module_id: str) -> Optional[BaseModule]:
        """
        获取指定模块

        Args:
            module_id: 模块ID

        Returns:
            模块实例，不存在则返回 None
        """
        return cls._modules.get(module_id)

    @classmethod
    def get_all(cls) -> List[BaseModule]:
        """
        获取所有已注册的模块

        Returns:
            模块列表
        """
        return list(cls._modules.values())

    @classmethod
    def get_module_ids(cls) -> List[str]:
        """
        获取所有模块ID

        Returns:
            模块ID列表
        """
        return list(cls._modules.keys())

    @classmethod
    async def get_enabled_modules(
        cls,
        user_id: str,
        db_session: "AsyncSession"
    ) -> List[BaseModule]:
        """
        获取用户已启用的模块列表

        如果用户没有任何订阅记录，则自动订阅所有模块

        Args:
            user_id: 用户ID
            db_session: 数据库会话

        Returns:
            用户已启用的模块列表
        """
        from services.modules.subscription import SubscriptionService

        subscription_service = SubscriptionService(db_session)

        # 获取用户已启用的模块ID列表
        enabled_ids = await subscription_service.get_enabled_modules(user_id)

        # 如果用户没有任何订阅，自动订阅所有模块
        if enabled_ids is None:
            logger.info(f"用户 {user_id} 首次使用，自动订阅所有模块")
            await subscription_service.subscribe_all(user_id)
            return cls.get_all()

        # 返回已启用的模块
        return [cls._modules[mid] for mid in enabled_ids if mid in cls._modules]

    @classmethod
    def is_registered(cls) -> bool:
        """检查模块是否已初始化注册"""
        return cls._initialized

    @classmethod
    def mark_initialized(cls) -> None:
        """标记模块已初始化"""
        cls._initialized = True
        logger.info(f"模块系统初始化完成，共 {len(cls._modules)} 个模块")


# 全局注册表实例
registry = ModuleRegistry()
