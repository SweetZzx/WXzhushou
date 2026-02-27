"""
模块订阅模型
记录用户对各个功能模块的订阅状态
"""
from datetime import datetime

from sqlalchemy import String, Boolean, DateTime, func
from sqlalchemy.orm import Mapped, mapped_column

from database.base import Base


class ModuleSubscription(Base):
    """
    模块订阅表

    记录每个用户对各个模块的订阅状态
    """
    __tablename__ = "module_subscriptions"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)

    # 用户ID（微信 openid）
    user_id: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
        index=True,
        comment="用户ID"
    )

    # 模块ID（如 schedule, contact 等）
    module_id: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        comment="模块ID"
    )

    # 是否启用
    enabled: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
        comment="是否启用"
    )

    # 订阅时间
    subscribed_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=func.now(),
        nullable=False,
        comment="订阅时间"
    )

    # 更新时间
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=func.now(),
        onupdate=func.now(),
        nullable=False,
        comment="更新时间"
    )

    def __repr__(self) -> str:
        status = "启用" if self.enabled else "禁用"
        return f"<ModuleSubscription user={self.user_id}, module={self.module_id}, {status}>"
