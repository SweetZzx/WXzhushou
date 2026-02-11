"""
日程数据模型
"""
from sqlalchemy import String, DateTime, Integer, Text, Index
from sqlalchemy.orm import Mapped, mapped_column
from datetime import datetime
from typing import Optional
from database.base import Base


class Schedule(Base):
    """日程表"""
    __tablename__ = "schedules"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    scheduled_time: Mapped[datetime] = mapped_column(DateTime, nullable=False, index=True)
    remind_before: Mapped[int] = mapped_column(Integer, default=0)
    status: Mapped[str] = mapped_column(String(20), default="active", index=True)
    job_id: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    # 复合索引
    __table_args__ = (
        Index("idx_user_time", "user_id", "scheduled_time"),
        Index("idx_status", "status"),
    )

    def __repr__(self):
        return f"<Schedule(id={self.id}, title='{self.title}', time={self.scheduled_time})>"

    def to_dict(self):
        """转换为字典"""
        return {
            "id": self.id,
            "user_id": self.user_id,
            "title": self.title,
            "description": self.description,
            "scheduled_time": self.scheduled_time.isoformat() if self.scheduled_time else None,
            "remind_before": self.remind_before,
            "status": self.status,
            "job_id": self.job_id,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
        }
