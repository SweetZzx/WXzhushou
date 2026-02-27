"""
日程模块的 Action 定义
"""
from typing import Optional
from pydantic import BaseModel, Field


class ScheduleAction(BaseModel):
    """日程操作"""
    type: str = Field(default="", description="操作类型: create/query/update/delete/settings/update_settings")
    title: Optional[str] = Field(default=None, description="日程标题")
    time: Optional[str] = Field(default=None, description="时间描述（如：明天下午3点）")
    date: Optional[str] = Field(default=None, description="日期描述（如：今天、明天、所有）")
    target: Optional[str] = Field(default=None, description="目标日程ID或关键词")
    # 设置相关
    daily_reminder_enabled: Optional[bool] = Field(default=None, description="是否开启每日提醒")
    daily_reminder_time: Optional[str] = Field(default=None, description="每日提醒时间")
    pre_reminder_enabled: Optional[bool] = Field(default=None, description="是否开启日程前提醒")
    pre_reminder_minutes: Optional[int] = Field(default=None, description="日程前多少分钟提醒")
