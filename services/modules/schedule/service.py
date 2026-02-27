"""
日程服务
处理日程的增删改查
"""
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_
from typing import List, Optional
from datetime import datetime, timedelta
import logging

from models.schedule import Schedule
from utils.time_parser import parse_time, format_time

logger = logging.getLogger(__name__)


class ScheduleService:
    """日程服务"""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def create_schedule(
        self,
        user_id: str,
        title: str,
        time_str: str,
        description: Optional[str] = None,
        remind_before: int = 0
    ) -> Optional[Schedule]:
        """创建日程"""
        try:
            # 解析时间
            scheduled_time = parse_time(time_str)
            if not scheduled_time:
                logger.error(f"无法解析时间: {time_str}")
                return None

            # 验证时间不能是过去
            if scheduled_time < datetime.now():
                logger.warning(f"日程时间不能是过去: {scheduled_time}")
                return None

            # 创建日程
            schedule = Schedule(
                user_id=user_id,
                title=title,
                description=description,
                scheduled_time=scheduled_time,
                remind_before=remind_before,
                status="active"
            )

            self.db.add(schedule)
            await self.db.commit()
            await self.db.refresh(schedule)

            logger.info(f"创建日程成功: user_id={user_id}, title={title}, time={scheduled_time}")
            return schedule

        except Exception as e:
            logger.error(f"创建日程失败: {e}", exc_info=True)
            await self.db.rollback()
            return None

    async def get_schedule(self, schedule_id: int, user_id: str) -> Optional[Schedule]:
        """获取指定日程"""
        try:
            result = await self.db.execute(
                select(Schedule).where(
                    and_(
                        Schedule.id == schedule_id,
                        Schedule.user_id == user_id
                    )
                )
            )
            return result.scalar_one_or_none()
        except Exception as e:
            logger.error(f"获取日程失败: {e}")
            return None

    async def list_schedules(
        self,
        user_id: str,
        date_str: Optional[str] = None,
        status: str = "active"
    ) -> List[Schedule]:
        """获取用户的日程列表"""
        try:
            query = select(Schedule).where(
                and_(
                    Schedule.user_id == user_id,
                    Schedule.status == status
                )
            )

            # 时间筛选
            if date_str:
                start_time, end_time = self._parse_date_range(date_str)
                if start_time and end_time:
                    query = query.where(
                        and_(
                            Schedule.scheduled_time >= start_time,
                            Schedule.scheduled_time < end_time
                        )
                    )

            query = query.order_by(Schedule.scheduled_time)

            result = await self.db.execute(query)
            return result.scalars().all()

        except Exception as e:
            logger.error(f"获取日程列表失败: {e}")
            return []

    async def update_schedule(
        self,
        schedule_id: int,
        user_id: str,
        title: Optional[str] = None,
        time_str: Optional[str] = None,
        description: Optional[str] = None
    ) -> Optional[Schedule]:
        """更新日程"""
        try:
            schedule = await self.get_schedule(schedule_id, user_id)
            if not schedule:
                return None

            if title:
                schedule.title = title
            if time_str:
                scheduled_time = parse_time(time_str)
                if scheduled_time:
                    schedule.scheduled_time = scheduled_time
            if description is not None:
                schedule.description = description

            schedule.updated_at = datetime.utcnow()
            await self.db.commit()
            await self.db.refresh(schedule)

            logger.info(f"更新日程成功: id={schedule_id}")
            return schedule

        except Exception as e:
            logger.error(f"更新日程失败: {e}")
            await self.db.rollback()
            return None

    async def delete_schedule(self, schedule_id: int, user_id: str) -> bool:
        """删除日程"""
        try:
            schedule = await self.get_schedule(schedule_id, user_id)
            if not schedule:
                return False

            await self.db.delete(schedule)
            await self.db.commit()

            logger.info(f"删除日程成功: id={schedule_id}")
            return True

        except Exception as e:
            logger.error(f"删除日程失败: {e}")
            await self.db.rollback()
            return False

    async def complete_schedule(self, schedule_id: int, user_id: str) -> bool:
        """完成日程"""
        try:
            schedule = await self.get_schedule(schedule_id, user_id)
            if not schedule:
                return False

            schedule.status = "completed"
            schedule.completed_at = datetime.utcnow()
            await self.db.commit()

            logger.info(f"完成日程: id={schedule_id}")
            return True

        except Exception as e:
            logger.error(f"完成日程失败: {e}")
            await self.db.rollback()
            return False

    async def find_schedules_by_keyword(
        self,
        user_id: str,
        keyword: str,
        date_str: Optional[str] = None
    ) -> List[Schedule]:
        """通过关键词查找日程"""
        try:
            query = select(Schedule).where(
                and_(
                    Schedule.user_id == user_id,
                    Schedule.status == "active",
                    Schedule.title.contains(keyword)
                )
            )

            # 时间筛选
            if date_str:
                start_time, end_time = self._parse_date_range(date_str)
                if start_time and end_time:
                    query = query.where(
                        and_(
                            Schedule.scheduled_time >= start_time,
                            Schedule.scheduled_time < end_time
                        )
                    )

            query = query.order_by(Schedule.scheduled_time)

            result = await self.db.execute(query)
            return result.scalars().all()

        except Exception as e:
            logger.error(f"搜索日程失败: {e}")
            return []

    def _parse_date_range(self, date_str: str) -> tuple[Optional[datetime], Optional[datetime]]:
        """解析日期范围"""
        now = datetime.now()

        if "今天" in date_str:
            start = now.replace(hour=0, minute=0, second=0, microsecond=0)
            end = start + timedelta(days=1)
            return (start, end)
        elif "明天" in date_str:
            start = (now + timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)
            end = start + timedelta(days=1)
            return (start, end)
        elif "后天" in date_str:
            start = (now + timedelta(days=2)).replace(hour=0, minute=0, second=0, microsecond=0)
            end = start + timedelta(days=1)
            return (start, end)
        elif "本周" in date_str:
            days_since_monday = now.weekday()
            monday = now - timedelta(days=days_since_monday)
            start = monday.replace(hour=0, minute=0, second=0, microsecond=0)
            end = start + timedelta(days=7)
            return (start, end)
        elif "下周" in date_str:
            days_since_monday = now.weekday()
            next_monday = now + timedelta(days=(7 - days_since_monday))
            start = next_monday.replace(hour=0, minute=0, second=0, microsecond=0)
            end = start + timedelta(days=7)
            return (start, end)

        return (None, None)

    def format_schedule(self, schedule: Schedule) -> str:
        """格式化日程显示"""
        time_str = format_time(schedule.scheduled_time)

        result = f"标题：{schedule.title}\n"
        result += f"时间：{time_str}"

        if schedule.description:
            result += f"\n备注：{schedule.description}"

        return result
