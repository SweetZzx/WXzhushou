"""
联系人数据模型
"""
from sqlalchemy import String, Integer, Text, Date, Index
from sqlalchemy.orm import Mapped, mapped_column
from datetime import datetime, date
from typing import Optional
from database.base import Base


class Contact(Base):
    """联系人表"""
    __tablename__ = "contacts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    phone: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)  # 加密存储
    birthday: Mapped[Optional[str]] = mapped_column(String(10), nullable=True)  # 格式: MM-DD
    remark: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    extra: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # 其他信息
    created_at: Mapped[datetime] = mapped_column(String(50), default=lambda: datetime.now().isoformat())
    updated_at: Mapped[datetime] = mapped_column(String(50), default=lambda: datetime.now().isoformat())

    # 复合索引
    __table_args__ = (
        Index("idx_user_name", "user_id", "name"),
    )

    def __repr__(self):
        return f"<Contact(id={self.id}, name='{self.name}')>"

    def to_dict(self, include_phone: bool = True):
        """转换为字典"""
        return {
            "id": self.id,
            "user_id": self.user_id,
            "name": self.name,
            "phone": self.phone if include_phone else "***",
            "birthday": self.birthday,
            "remark": self.remark,
            "extra": self.extra,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }
