"""
用户设置数据模型
存储用户的提醒偏好设置
"""
from sqlalchemy import String, Integer, Boolean, DateTime
from sqlalchemy.orm import Mapped, mapped_column
from datetime import datetime
from typing import Optional
from database.base import Base


class UserSettings(Base):
    """用户设置表"""
    __tablename__ = "user_settings"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[str] = mapped_column(String(100), nullable=False, unique=True, index=True)

    # 每日日程提醒设置
    daily_reminder_enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    daily_reminder_time: Mapped[str] = mapped_column(String(10), default="08:00")  # HH:MM 格式

    # 日程开始前提醒设置
    pre_schedule_reminder_enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    pre_schedule_reminder_minutes: Mapped[int] = mapped_column(Integer, default=10)  # 提前多少分钟提醒

    # 其他设置
    timezone: Mapped[str] = mapped_column(String(50), default="Asia/Shanghai")

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def __repr__(self):
        return f"<UserSettings(user_id='{self.user_id}', daily_time='{self.daily_reminder_time}')>"

    def to_dict(self):
        """转换为字典"""
        return {
            "user_id": self.user_id,
            "daily_reminder_enabled": self.daily_reminder_enabled,
            "daily_reminder_time": self.daily_reminder_time,
            "pre_schedule_reminder_enabled": self.pre_schedule_reminder_enabled,
            "pre_schedule_reminder_minutes": self.pre_schedule_reminder_minutes,
            "timezone": self.timezone,
        }
