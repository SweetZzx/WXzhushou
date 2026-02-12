"""
时间解析工具
支持中文自然语言时间表达式解析
"""
from datetime import datetime, timedelta
import dateparser
import re
import logging
from typing import Optional, Tuple

logger = logging.getLogger(__name__)


class TimeParser:
    """时间解析器"""

    # 中文时间关键词映射
    TIME_KEYWORDS = {
        "今天": 0,
        "明天": 1,
        "后天": 2,
        "大后天": 3,
        "本周": "this_week",
        "下周": "next_week",
        "这周": "this_week",
        "上周": "last_week",
        "这个月": "this_month",
        "下个月": "next_month",
    }

    # 时间段映射
    TIME_PERIODS = {
        "上午": "morning",
        "下午": "afternoon",
        "早上": "morning",
        "晚上": "evening",
        "中午": "noon",
        "半夜": "midnight",
        "凌晨": "early_morning",
    }

    @staticmethod
    def parse(time_str: str, reference_time: Optional[datetime] = None) -> Optional[datetime]:
        """
        解析时间字符串

        Args:
            time_str: 时间字符串，如 "明天下午3点"、"2024-02-12 15:00"
            reference_time: 参考时间，默认为当前时间

        Returns:
            解析后的 datetime 对象，失败返回 None
        """
        if reference_time is None:
            reference_time = datetime.now()

        if not time_str or not time_str.strip():
            return None

        try:
            # 1. 先尝试直接解析标准格式
            # 处理 "2024-02-12 15:00" 格式
            standard_pattern = r"(\d{4})-(\d{1,2})-(\d{1,2})\s+(\d{1,2}):(\d{2})"
            match = re.match(standard_pattern, time_str)
            if match:
                year, month, day, hour, minute = map(int, match.groups())
                return datetime(year, month, day, hour, minute)

            # 2. 处理相对时间（带日期关键词）
            result = TimeParser._parse_relative_time(time_str, reference_time)
            if result:
                return result

            # 3. 尝试提取纯时间（如 "下午六点"、"3点"），默认使用今天
            time_part = TimeParser._extract_time(time_str)
            if time_part:
                hour, minute = time_part
                result = reference_time.replace(hour=hour, minute=minute, second=0, microsecond=0)
                # 如果时间已过，则设为明天
                if result < reference_time:
                    result += timedelta(days=1)
                return result

            # 4. 使用 dateparser 解析
            settings = {
                "PREFER_DATES_FROM": "future",
                "RELATIVE_BASE": reference_time,
            }
            result = dateparser.parse(time_str, languages=["zh"], settings=settings)
            if result:
                return result

            logger.warning(f"无法解析时间字符串: {time_str}")
            return None

        except Exception as e:
            logger.error(f"解析时间时出错: {e}, time_str={time_str}")
            return None

    @staticmethod
    def _parse_relative_time(time_str: str, reference_time: datetime) -> Optional[datetime]:
        """解析相对时间表达式"""
        # 检查是否包含日期关键词
        for keyword, value in TimeParser.TIME_KEYWORDS.items():
            if keyword in time_str:
                if isinstance(value, int):
                    # "明天"、"后天" 等
                    base_date = reference_time + timedelta(days=value)
                elif value == "this_week":
                    # 本周（下周一）
                    base_date = TimeParser._get_weekday(reference_time, 0)
                elif value == "next_week":
                    # 下周一
                    base_date = TimeParser._get_weekday(reference_time, 7)
                elif value == "last_week":
                    # 上周一
                    base_date = TimeParser._get_weekday(reference_time, -7)
                elif value == "this_month":
                    # 本月1号
                    base_date = reference_time.replace(day=1)
                elif value == "next_month":
                    # 下月1号
                    if reference_time.month == 12:
                        base_date = reference_time.replace(year=reference_time.year + 1, month=1, day=1)
                    else:
                        base_date = reference_time.replace(month=reference_time.month + 1, day=1)
                else:
                    base_date = reference_time

                # 解析时间部分
                time_part = TimeParser._extract_time(time_str)
                if time_part:
                    hour, minute = time_part
                    return base_date.replace(hour=hour, minute=minute, second=0, microsecond=0)
                else:
                    # 没有具体时间，默认为早上9点
                    return base_date.replace(hour=9, minute=0, second=0, microsecond=0)

        return None

    # 中文数字映射
    CHINESE_NUMBERS = {
        "零": 0, "一": 1, "二": 2, "三": 3, "四": 4, "五": 5,
        "六": 6, "七": 7, "八": 8, "九": 9, "十": 10,
        "十一": 11, "十二": 12, "十三": 13, "十四": 14, "十五": 15,
        "十六": 16, "十七": 17, "十八": 18, "十九": 19, "二十": 20,
        "二十一": 21, "二十二": 22, "二十三": 23, "二十四": 24,
    }

    @staticmethod
    def _extract_time(time_str: str) -> Optional[Tuple[int, int]]:
        """从字符串中提取时间（小时和分钟）"""
        # 先尝试转换中文数字
        converted_str = time_str
        for cn_num, ar_num in TimeParser.CHINESE_NUMBERS.items():
            converted_str = converted_str.replace(cn_num, str(ar_num))

        # 匹配 "3点"、"15点"、"下午3点"、"15:30" 等格式
        patterns = [
            r"(\d{1,2})点(\d{1,2})分?",  # 3点、3点30、15点
            r"(\d{1,2}):(\d{2})",  # 15:30
            r"(\d{1,2})\.(\d{2})",  # 15.30
            r"(\d{1,2})点",  # 6点、15点（无分钟）
        ]

        for pattern in patterns:
            match = re.search(pattern, converted_str)
            if match:
                hour = int(match.group(1))
                minute = int(match.group(2)) if len(match.groups()) > 1 and match.group(2) else 0

                # 处理上午/下午
                if "下午" in time_str or "晚上" in time_str:
                    if hour < 12:
                        hour += 12
                elif "上午" in time_str or "早上" in time_str or "凌晨" in time_str:
                    if hour >= 12:
                        hour -= 12

                # 验证时间范围
                if 0 <= hour <= 23 and 0 <= minute <= 59:
                    return (hour, minute)

        return None

    @staticmethod
    def _get_weekday(reference_time: datetime, offset: int) -> datetime:
        """获取指定偏移量的周一"""
        days_since_monday = reference_time.weekday()
        monday = reference_time - timedelta(days=days_since_monday)
        target_monday = monday + timedelta(days=offset)
        return target_monday

    @staticmethod
    def format_time(dt: datetime) -> str:
        """格式化时间显示"""
        now = datetime.now()
        delta = dt - now

        if delta.days == 0:
            # 今天
            return f"今天 {dt.strftime('%H:%M')}"
        elif delta.days == 1:
            # 明天
            return f"明天 {dt.strftime('%H:%M')}"
        elif delta.days == 2:
            # 后天
            return f"后天 {dt.strftime('%H:%M')}"
        elif 0 < delta.days <= 7:
            # 本周
            weekdays = ["周一", "周二", "周三", "周四", "周五", "周六", "周日"]
            return f"{weekdays[dt.weekday()]} {dt.strftime('%H:%M')}"
        else:
            # 具体日期
            return dt.strftime("%Y-%m-%d %H:%M")


# 便捷函数
def parse_time(time_str: str, reference_time: Optional[datetime] = None) -> Optional[datetime]:
    """解析时间字符串（便捷函数）"""
    return TimeParser.parse(time_str, reference_time)


def format_time(dt: datetime) -> str:
    """格式化时间显示（便捷函数）"""
    return TimeParser.format_time(dt)
