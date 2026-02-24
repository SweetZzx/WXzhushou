"""
LangChain 工具定义
使用 @tool 装饰器定义日程管理工具
"""
import logging
from datetime import datetime, timedelta
from typing import Optional, List

from langchain.tools import tool

from services.schedule_service import ScheduleService
from services.reminder_service import reminder_service

logger = logging.getLogger(__name__)


def get_tools(schedule_service: ScheduleService, user_id: str) -> List:
    """
    获取日程管理工具集

    Args:
        schedule_service: 日程服务实例
        user_id: 当前用户 ID

    Returns:
        工具列表
    """
    weekdays = ["星期一", "星期二", "星期三", "星期四", "星期五", "星期六", "星期日"]

    @tool
    async def get_current_datetime() -> str:
        """获取当前的日期和时间（ISO格式）。处理任何涉及时间的请求前，必须先调用此函数获取当前时间作为参考。"""
        now = datetime.now()
        return (
            f"当前时间（ISO格式）：{now.strftime('%Y-%m-%d %H:%M:%S')}\n"
            f"日期：{now.strftime('%Y年%m月%d日')}\n"
            f"星期：{weekdays[now.weekday()]}\n\n"
            f"请根据此时间计算用户指定的日期，输出格式为 YYYY-MM-DD HH:MM"
        )

    @tool
    async def get_current_time() -> str:
        """获取当前的日期和时间。当用户询问现在几点、今天几号、今天星期几时使用。"""
        now = datetime.now()
        return (
            f"当前时间信息：\n"
            f"日期：{now.strftime('%Y年%m月%d日')}\n"
            f"时间：{now.strftime('%H:%M:%S')}\n"
            f"星期：{weekdays[now.weekday()]}"
        )

    @tool
    async def parse_time_to_iso(natural_time: str) -> str:
        """将自然语言时间转换为ISO格式。创建或修改日程前，必须先调用此函数将用户说的时间转换为YYYY-MM-DD HH:MM格式。

        Args:
            natural_time: 用户说的自然语言时间，如：明天下午三点、后天晚上十点、周五上午9点、22号
        """
        from utils.time_parser import parse_time
        now = datetime.now()
        logger.info(f"解析自然语言时间: '{natural_time}'")
        parsed = parse_time(natural_time, now)
        if parsed:
            iso_time = parsed.strftime("%Y-%m-%d %H:%M")
            logger.info(f"解析结果: '{natural_time}' -> {iso_time}")
            return f"时间解析结果：{iso_time}\n请使用这个ISO格式时间调用create_schedule。"
        return f"无法解析时间：{natural_time}，请让用户更明确地说明时间。"

    @tool
    async def get_date_info(date_str: str = "今天") -> str:
        """获取指定日期的详细信息。当用户询问明天是几号、下周一是哪天时使用。

        Args:
            date_str: 要查询的日期，如：今天、明天、后天、下周
        """
        now = datetime.now()
        if date_str in ["今天", "今日"]:
            target = now
        elif date_str in ["明天", "明日"]:
            target = now + timedelta(days=1)
        elif date_str in ["后天"]:
            target = now + timedelta(days=2)
        elif date_str in ["昨天", "昨日"]:
            target = now - timedelta(days=1)
        else:
            target = now

        days_diff = (target.date() - now.date()).days
        if days_diff == 0:
            diff_str = "今天"
        elif days_diff > 0:
            diff_str = f"距今{days_diff}天"
        else:
            diff_str = f"距今{abs(days_diff)}天前"

        return (
            f"日期信息：\n"
            f"日期：{target.strftime('%Y年%m月%d日')}\n"
            f"星期：{weekdays[target.weekday()]}\n"
            f"{diff_str}"
        )

    @tool
    async def create_schedule(title: str, datetime_str: str, description: str = "") -> str:
        """创建新日程。⚠️调用前必须先调用parse_time_to_iso获取ISO格式的时间！datetime参数只接受YYYY-MM-DD HH:MM格式。

        Args:
            title: 日程标题，如：开会、看病、健身
            datetime_str: 日程时间。⚠️必须是精确格式YYYY-MM-DD HH:MM，如2026-02-24 09:00。禁止传入'明天下午三点'等自然语言！
            description: 日程的详细描述（可选）
        """
        logger.info(f"创建日程: title={title}, datetime={datetime_str}, description={description}")
        schedule = await schedule_service.create_schedule(
            user_id=user_id,
            title=title,
            time_str=datetime_str,
            description=description or None
        )
        if schedule:
            return f"日程创建成功！\n{schedule_service.format_schedule(schedule)}"
        return "创建日程失败，请检查时间格式是否正确。"

    @tool
    async def query_schedules(date: str = "今天") -> str:
        """查询指定日期的日程。当用户想查看某天的安排时使用。注意：必须准确传递用户说的日期！

        Args:
            date: 查询日期。必须准确传递用户指定的值：如果用户说'明天'就传'明天'，说'今天'就传'今天'。可选值：今天、明天、后天、本周、下周
        """
        schedules = await schedule_service.list_schedules(user_id=user_id, date_str=date)
        if not schedules:
            return f"📭 {date}没有日程安排。"

        result = f"📅 {date}的日程：\n\n"
        for i, schedule in enumerate(schedules, 1):
            result += f"{i}. {schedule_service.format_schedule(schedule)}\n\n"
        return result.strip()

    @tool
    async def list_all_schedules() -> str:
        """列出用户的所有日程（带ID）。当用户想看所有日程、或需要知道日程ID以便修改/删除时使用。"""
        # 获取最近7天的日程
        all_schedules = []
        for day_offset in range(7):
            date_str = "今天" if day_offset == 0 else ("明天" if day_offset == 1 else ("后天" if day_offset == 2 else f"{day_offset}天后"))
            schedules = await schedule_service.list_schedules(user_id=user_id, date_str=date_str if day_offset <= 2 else None)
            for s in schedules:
                if s not in all_schedules:
                    all_schedules.append(s)

        if not all_schedules:
            return "您目前没有任何日程安排。"

        result = "📋 您的所有日程：\n\n"
        for schedule in all_schedules:
            result += f"[ID:{schedule.id}] {schedule_service.format_schedule(schedule)}\n\n"
        result += "提示：修改或删除日程时，请使用对应的ID。"
        return result.strip()

    @tool
    async def update_schedule(
        schedule_id: int,
        title: Optional[str] = None,
        datetime_str: Optional[str] = None,
        description: Optional[str] = None
    ) -> str:
        """修改已有日程。需要日程ID，如果用户不知道ID，先调用find_schedule_by_keyword或list_all_schedules。datetime参数必须是YYYY-MM-DD HH:MM格式。

        Args:
            schedule_id: 要修改的日程ID
            title: 新的日程标题（可选）
            datetime_str: 新的日程时间，必须是YYYY-MM-DD HH:MM格式（可选）
            description: 新的备注内容（可选）
        """
        schedule = await schedule_service.update_schedule(
            schedule_id=schedule_id,
            user_id=user_id,
            title=title,
            time_str=datetime_str,
            description=description
        )
        if schedule:
            return f"日程修改成功！\n{schedule_service.format_schedule(schedule)}"
        return f"修改失败，未找到日程或无权操作 (ID: {schedule_id})"

    @tool
    async def find_schedule_by_keyword(keyword: str, date: Optional[str] = None) -> str:
        """通过标题关键词搜索日程。当用户说'把开会那个日程改一下'、'修改健身的日程'等通过标题描述日程时使用。

        Args:
            keyword: 日程标题中的关键词，如：开会、健身、睡觉
            date: 日期筛选（可选）：今天、明天、后天
        """
        schedules = await schedule_service.find_schedules_by_keyword(
            user_id=user_id,
            keyword=keyword,
            date_str=date
        )
        if not schedules:
            date_hint = f" {date}" if date else ""
            return f"没有找到标题包含「{keyword}」的日程{date_hint}。"

        if len(schedules) == 1:
            s = schedules[0]
            return f"找到1个匹配的日程：\n[ID:{s.id}] {schedule_service.format_schedule(s)}\n\n请确认是否修改此日程。"

        result = f"找到 {len(schedules)} 个包含「{keyword}」的日程：\n\n"
        for s in schedules:
            result += f"[ID:{s.id}] {schedule_service.format_schedule(s)}\n\n"
        result += "请告诉我要修改哪一个（提供ID）。"
        return result.strip()

    @tool
    async def shift_schedule_time(schedule_id: int, shift_minutes: int) -> str:
        """偏移日程时间（提前或推迟）。当用户说'提前30分钟'、'推迟1小时'、'往后推一天'时使用。

        Args:
            schedule_id: 日程ID
            shift_minutes: 偏移分钟数。正数=推迟，负数=提前。如：提前30分钟=-30，推迟1小时=60，推迟1天=1440
        """
        schedule = await schedule_service.shift_schedule_time(
            schedule_id=schedule_id,
            user_id=user_id,
            shift_minutes=shift_minutes
        )
        if schedule:
            direction = "推迟" if shift_minutes > 0 else "提前"
            abs_min = abs(shift_minutes)
            if abs_min >= 1440:
                time_desc = f"{abs_min // 1440}天"
            elif abs_min >= 60:
                time_desc = f"{abs_min // 60}小时"
            else:
                time_desc = f"{abs_min}分钟"
            return f"已{direction}{time_desc}！\n{schedule_service.format_schedule(schedule)}"
        return f"时间调整失败，未找到日程或调整后时间已过 (ID: {schedule_id})"

    @tool
    async def delete_schedule(schedule_id: int) -> str:
        """删除日程。需要日程ID，如果用户不知道ID，先调用list_all_schedules。

        Args:
            schedule_id: 要删除的日程ID
        """
        success = await schedule_service.delete_schedule(schedule_id, user_id)
        if success:
            return f"已删除日程 (ID: {schedule_id})"
        return f"删除失败，未找到日程或无权操作 (ID: {schedule_id})"

    @tool
    async def get_reminder_settings() -> str:
        """获取用户的提醒设置。当用户询问提醒相关设置时使用。"""
        settings = await reminder_service.get_user_settings(user_id)
        if settings:
            daily_status = "已开启" if settings["daily_reminder_enabled"] else "已关闭"
            pre_status = "已开启" if settings["pre_schedule_reminder_enabled"] else "已关闭"
            return (
                f"⏰ 您的提醒设置：\n\n"
                f"📅 每日日程提醒：{daily_status}\n"
                f"   - 提醒时间：{settings['daily_reminder_time']}\n\n"
                f"🔔 日程开始前提醒：{pre_status}\n"
                f"   - 提前 {settings['pre_schedule_reminder_minutes']} 分钟提醒"
            )
        return "获取提醒设置失败。"

    @tool
    async def update_reminder_settings(
        daily_reminder_enabled: Optional[bool] = None,
        daily_reminder_time: Optional[str] = None,
        pre_schedule_reminder_enabled: Optional[bool] = None,
        pre_schedule_reminder_minutes: Optional[int] = None
    ) -> str:
        """更新用户的提醒设置。当用户想修改提醒开关或时间时使用。

        Args:
            daily_reminder_enabled: 是否开启每日日程提醒（true/false）
            daily_reminder_time: 每日提醒时间，格式：HH:MM，如 08:00
            pre_schedule_reminder_enabled: 是否开启日程开始前提醒（true/false）
            pre_schedule_reminder_minutes: 日程开始前多少分钟提醒，如 10、15、30
        """
        settings = await reminder_service.update_user_settings(
            user_id=user_id,
            daily_reminder_enabled=daily_reminder_enabled,
            daily_reminder_time=daily_reminder_time,
            pre_schedule_reminder_enabled=pre_schedule_reminder_enabled,
            pre_schedule_reminder_minutes=pre_schedule_reminder_minutes
        )
        if settings:
            daily_status = "已开启" if settings.daily_reminder_enabled else "已关闭"
            pre_status = "已开启" if settings.pre_schedule_reminder_enabled else "已关闭"
            return (
                f"✅ 提醒设置已更新！\n\n"
                f"📅 每日日程提醒：{daily_status}（{settings.daily_reminder_time}）\n"
                f"🔔 日程开始前提醒：{pre_status}（提前 {settings.pre_schedule_reminder_minutes} 分钟）"
            )
        return "更新提醒设置失败。"

    return [
        get_current_datetime,
        get_current_time,
        parse_time_to_iso,
        get_date_info,
        create_schedule,
        query_schedules,
        list_all_schedules,
        update_schedule,
        find_schedule_by_keyword,
        shift_schedule_time,
        delete_schedule,
        get_reminder_settings,
        update_reminder_settings,
    ]
