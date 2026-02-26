"""
时间解析工具
支持中文自然语言时间表达式解析

参考资源：
- JioNLP 时间语义解析: https://github.com/dongrixinyu/JioNLP/wiki/时间语义解析-说明文档
- 中文时间表达: https://talkpal.ai/vocabulary/汉语时间相关词汇/
"""
from datetime import datetime, timedelta
import dateparser
import re
import logging
from typing import Optional, Tuple

logger = logging.getLogger(__name__)


class TimeParser:
    """时间解析器 - 支持丰富的中文时间表达"""

    # ============================================
    # 日期关键词映射
    # ============================================
    DATE_KEYWORDS = {
        # 相对日期
        "大前天": -3,
        "前天": -2,
        "昨天": -1,
        "今天": 0,
        "今日": 0,
        "明日": 1,
        "明天": 1,
        "后天": 2,
        "大后天": 3,
        # 月
        "上个月": "last_month",
        "这个月": "this_month",
        "本月": "this_month",
        "下个月": "next_month",
        # 年
        "去年": "last_year",
        "今年": "this_year",
        "明年": "next_year",
    }

    # 周前缀（用于周几匹配）
    WEEK_PREFIXES = {
        "上上周": -14,
        "上周": -7,
        "这周": 0,
        "本周": 0,
        "下周": 7,
        "下下周": 14,
    }

    # 星期映射
    WEEKDAY_MAP = {
        "周一": 0, "星期一": 0, "礼拜一": 0,
        "周二": 1, "星期二": 1, "礼拜二": 1,
        "周三": 2, "星期三": 2, "礼拜三": 2,
        "周四": 3, "星期四": 3, "礼拜四": 3,
        "周五": 4, "星期五": 4, "礼拜五": 4,
        "周六": 5, "星期六": 5, "礼拜六": 5,
        "周天": 6, "周日": 6, "星期日": 6, "礼拜日": 6, "星期天": 6,
    }

    # 时间段映射 - 用于推断默认小时和处理上午/下午
    TIME_PERIODS = {
        "凌晨": {"hours": (0, 5), "default": 2, "adjust": None},
        "早上": {"hours": (6, 8), "default": 7, "adjust": None},
        "上午": {"hours": (9, 11), "default": 10, "adjust": None},
        "中午": {"hours": (12, 13), "default": 12, "adjust": "noon"},
        "午间": {"hours": (12, 14), "default": 12, "adjust": "noon"},
        "下午": {"hours": (14, 17), "default": 15, "adjust": "pm"},
        "傍晚": {"hours": (17, 19), "default": 18, "adjust": "pm"},
        "晚上": {"hours": (19, 22), "default": 20, "adjust": "pm"},
        "晚间": {"hours": (19, 23), "default": 20, "adjust": "pm"},
        "夜间": {"hours": (20, 24), "default": 22, "adjust": "pm"},
        "半夜": {"hours": (0, 3), "default": 0, "adjust": None},
        "深夜": {"hours": (23, 3), "default": 23, "adjust": None},
    }

    # 即时表达
    IMMEDIATE_KEYWORDS = {
        "即刻": 0,
        "马上": 0,
        "现在": 0,
        "立刻": 0,
        " right now": 0,  # 英文兼容
    }

    # 中文数字映射（按长度降序处理，确保复合数字优先匹配）
    CHINESE_NUMBERS = {
        # 基本数字
        "零": 0, "〇": 0,
        "一": 1, "壹": 1,
        "二": 2, "贰": 2, "两": 2,
        "三": 3, "叁": 3,
        "四": 4, "肆": 4,
        "五": 5, "伍": 5,
        "六": 6, "陆": 6,
        "七": 7, "柒": 7,
        "八": 8, "捌": 8,
        "九": 9, "玖": 9,
        "十": 10, "拾": 10,
        # 11-19
        "十一": 11, "十二": 12, "十三": 13, "十四": 14, "十五": 15,
        "十六": 16, "十七": 17, "十八": 18, "十九": 19,
        # 20-29
        "二十": 20, "二十一": 21, "二十二": 22, "二十三": 23, "二十四": 24,
        "二十五": 25, "二十六": 26, "二十七": 27, "二十八": 28, "二十九": 29,
        # 30-39
        "三十": 30, "三十一": 31, "三十二": 32, "三十三": 33, "三十四": 34,
        "三十五": 35, "三十六": 36, "三十七": 37, "三十八": 38, "三十九": 39,
        # 40-49
        "四十": 40, "四十一": 41, "四十二": 42, "四十三": 43, "四十四": 44,
        "四十五": 45, "四十六": 46, "四十七": 47, "四十八": 48, "四十九": 49,
        # 50-59
        "五十": 50, "五十一": 51, "五十二": 52, "五十三": 53, "五十四": 54,
        "五十五": 55, "五十六": 56, "五十七": 57, "五十八": 58, "五十九": 59,
        # 廿（二十的简写）
        "廿": 20, "廿一": 21, "廿二": 22, "廿三": 23, "廿四": 24,
        "廿五": 25, "廿六": 26, "廿七": 27, "廿八": 28, "廿九": 29,
    }

    @staticmethod
    def parse(time_str: str, reference_time: Optional[datetime] = None) -> Optional[datetime]:
        """
        解析时间字符串

        Args:
            time_str: 时间字符串，支持格式：
                      - ISO格式: "2024-02-12 15:00"
                      - 月日格式: "3月15日"、"三月十五号"
                      - 相对日期: "今天"、"明天"、"后天"、"大后天"
                      - 周相关: "这周五"、"下周三"、"下下周一"
                      - 时间点: "下午三点"、"晚上十点"、"凌晨2点"、"三点半"
                      - 组合: "明天下午三点"、"3月15日下午3点半"
                      - 即时: "即刻"、"马上"、"现在"
            reference_time: 参考时间，默认为当前时间

        Returns:
            解析后的 datetime 对象，失败返回 None
        """
        if reference_time is None:
            reference_time = datetime.now()

        if not time_str or not time_str.strip():
            return None

        time_str = time_str.strip()

        try:
            # 0. 检查即时表达
            for keyword in TimeParser.IMMEDIATE_KEYWORDS:
                if keyword in time_str:
                    logger.info(f"即时表达解析: '{time_str}' -> {reference_time}")
                    return reference_time

            # 1. 优先解析ISO格式 "2024-02-12 15:00"
            standard_pattern = r"(\d{4})-(\d{1,2})-(\d{1,2})\s+(\d{1,2}):(\d{2})"
            match = re.match(standard_pattern, time_str)
            if match:
                year, month, day, hour, minute = map(int, match.groups())
                result = datetime(year, month, day, hour, minute)
                logger.info(f"ISO格式解析成功: '{time_str}' -> {result}")
                return result

            # 2. 解析月日格式 "3月15日"、"三月十五号"
            result = TimeParser._parse_month_day(time_str, reference_time)
            if result:
                logger.info(f"月日格式解析成功: '{time_str}' -> {result}")
                return result

            # 3. 解析带日期关键词的复杂时间表达式
            result = TimeParser._parse_complex_time(time_str, reference_time)
            if result:
                logger.info(f"复杂时间解析成功: '{time_str}' -> {result}")
                return result

            # 4. 使用 dateparser 作为最后的fallback
            settings = {
                "PREFER_DATES_FROM": "future",
                "RELATIVE_BASE": reference_time,
            }
            result = dateparser.parse(time_str, languages=["zh"], settings=settings)
            if result:
                logger.info(f"dateparser解析成功: '{time_str}' -> {result}")
                return result

            logger.warning(f"无法解析时间字符串: {time_str}")
            return None

        except Exception as e:
            logger.error(f"解析时间时出错: {e}, time_str={time_str}")
            return None

    @staticmethod
    def _parse_complex_time(time_str: str, reference_time: datetime) -> Optional[datetime]:
        """解析复杂的时间表达式"""
        # 先提取日期部分（使用原始文本，避免数字转换破坏周几匹配）
        date_result = TimeParser._extract_date(time_str, reference_time)
        if date_result is None:
            date_result = reference_time

        # 转换中文数字（用于时间解析）
        converted = TimeParser._convert_chinese_numbers(time_str)

        # 提取时间部分
        time_result = TimeParser._extract_time(converted, time_str)

        if time_result:
            hour, minute = time_result
            result = date_result.replace(hour=hour, minute=minute, second=0, microsecond=0)

            # 如果只提取了时间没有日期，且时间已过，则设为明天
            if date_result.date() == reference_time.date() and result < reference_time:
                # 检查是否有明确的日期关键词
                has_date_keyword = any(kw in time_str for kw in TimeParser.DATE_KEYWORDS.keys())
                if not has_date_keyword:
                    result += timedelta(days=1)

            return result

        # 只有日期没有时间，默认9点
        if date_result.date() != reference_time.date():
            return date_result.replace(hour=9, minute=0, second=0, microsecond=0)

        return None

    @staticmethod
    def _convert_chinese_numbers(text: str) -> str:
        """将中文数字转换为阿拉伯数字"""
        result = text

        # 1. 先处理"半"的情况（在中文数字转换前）
        # "三点半" → "三点30"，而不是先转"三"成"3"再处理"半"
        result = re.sub(r'([一二三四五六七八九十两]+)点半', r'\1点30', result)
        result = re.sub(r'(\d+)点半', r'\1点30', result)

        # 2. 处理"刻"的情况
        result = re.sub(r'([一二三四五六七八九十]+)点一刻', r'\1点15', result)
        result = re.sub(r'([一二三四五六七八九十]+)点三刻', r'\1点45', result)
        result = re.sub(r'(\d+)点一刻', r'\1点15', result)
        result = re.sub(r'(\d+)点三刻', r'\1点45', result)

        # 3. 按长度降序排列，避免"十一"被替换成"11"后又替换"一"
        sorted_numbers = sorted(TimeParser.CHINESE_NUMBERS.items(), key=lambda x: -len(x[0]))
        for cn_num, ar_num in sorted_numbers:
            result = result.replace(cn_num, str(ar_num))

        return result

    @staticmethod
    def _parse_month_day(time_str: str, reference_time: datetime) -> Optional[datetime]:
        """
        解析月日格式
        支持: "3月15日"、"三月十五号"、"3/15"、"3-15"
        """
        original_str = time_str

        # 中文月日格式: "三月十五号"、"3月15日"、"三月15日"
        cn_month_day = r'([一二三四五六七八九十\d]+)月([一二三四五六七八九十廿\d]+)[日号]'
        match = re.search(cn_month_day, time_str)
        if match:
            month_str, day_str = match.groups()
            # 转换中文数字
            month_str = TimeParser._convert_chinese_numbers(month_str)
            day_str = TimeParser._convert_chinese_numbers(day_str)

            try:
                month = int(month_str)
                day = int(day_str)

                if 1 <= month <= 12 and 1 <= day <= 31:
                    # 默认今年
                    year = reference_time.year
                    result = datetime(year, month, day)

                    # 如果日期已过，尝试明年
                    if result.date() < reference_time.date():
                        result = datetime(year + 1, month, day)

                    # 提取时间部分（如果有）
                    time_result = TimeParser._extract_time(
                        TimeParser._convert_chinese_numbers(time_str),
                        time_str
                    )
                    if time_result:
                        hour, minute = time_result
                        result = result.replace(hour=hour, minute=minute)
                    else:
                        result = result.replace(hour=9, minute=0)

                    return result
            except (ValueError, TypeError):
                pass

        # 简写格式: "3/15"、"3-15"
        short_date = r'(\d{1,2})[/-](\d{1,2})'
        match = re.search(short_date, time_str)
        if match:
            try:
                month = int(match.group(1))
                day = int(match.group(2))

                if 1 <= month <= 12 and 1 <= day <= 31:
                    year = reference_time.year
                    result = datetime(year, month, day)

                    if result.date() < reference_time.date():
                        result = datetime(year + 1, month, day)

                    # 提取时间部分
                    time_result = TimeParser._extract_time(
                        TimeParser._convert_chinese_numbers(time_str),
                        time_str
                    )
                    if time_result:
                        hour, minute = time_result
                        result = result.replace(hour=hour, minute=minute)
                    else:
                        result = result.replace(hour=9, minute=0)

                    return result
            except (ValueError, TypeError):
                pass

        return None

    @staticmethod
    def _extract_date(text: str, reference_time: datetime) -> Optional[datetime]:
        """从文本中提取日期"""
        original_text = text

        # 0. 检查"X号"或"X日"格式（本月某天）- 最优先
        day_pattern = r'(\d{1,2})[号日]'
        day_match = re.search(day_pattern, original_text)
        if day_match:
            target_day = int(day_match.group(1))
            # 验证日期有效性
            if 1 <= target_day <= 31:
                # 先尝试当月
                try:
                    result = reference_time.replace(day=target_day)
                    # 如果日期已过，尝试下个月
                    if result.date() < reference_time.date():
                        # 切换到下个月
                        if reference_time.month == 12:
                            result = result.replace(year=reference_time.year + 1, month=1)
                        else:
                            result = result.replace(month=reference_time.month + 1)
                    logger.info(f"日期号解析: {target_day}号 -> {result.date()}")
                    return result
                except ValueError:
                    # 日期无效（如2月30日），尝试下个月
                    pass

        # 1. 优先检查周几（这周五、下周三、下下周一等）- 必须在基本关键词之前
        week_pattern = r'(下下周|下周|这周|本周|上上周|上周)?(周[一二三四五六七日天]|星期[一二三四五六七日天]|礼拜[一二三四五六七日天])'
        match = re.search(week_pattern, original_text)
        if match:
            week_prefix = match.group(1) or ""
            weekday_text = match.group(2)

            # 获取目标星期几
            target_weekday = None
            for wd_name, wd_num in TimeParser.WEEKDAY_MAP.items():
                if wd_name in weekday_text:
                    target_weekday = wd_num
                    break

            if target_weekday is not None:
                current_weekday = reference_time.weekday()

                if week_prefix == "":
                    # 没有前缀，默认这周
                    days_diff = target_weekday - current_weekday
                    if days_diff < 0:
                        days_diff += 7  # 如果已过，则为下周
                    return reference_time + timedelta(days=days_diff)
                elif week_prefix in ["这周", "本周"]:
                    # 这周
                    days_diff = target_weekday - current_weekday
                    if days_diff < 0:
                        days_diff += 7
                    return reference_time + timedelta(days=days_diff)
                elif week_prefix == "下周":
                    # 下周
                    days_until_sunday = 6 - current_weekday
                    days_to_target = days_until_sunday + 1 + target_weekday
                    return reference_time + timedelta(days=days_to_target)
                elif week_prefix == "下下周":
                    # 下下周
                    days_until_sunday = 6 - current_weekday
                    days_to_target = days_until_sunday + 1 + 7 + target_weekday
                    return reference_time + timedelta(days=days_to_target)
                elif week_prefix == "上周":
                    # 上周
                    days_since_monday = current_weekday
                    days_to_target = -(days_since_monday + 7 - target_weekday)
                    return reference_time + timedelta(days=days_to_target)
                elif week_prefix == "上上周":
                    # 上上周
                    days_since_monday = current_weekday
                    days_to_target = -(days_since_monday + 14 - target_weekday)
                    return reference_time + timedelta(days=days_to_target)

        # 2. 检查基本日期关键词
        for keyword, value in TimeParser.DATE_KEYWORDS.items():
            if keyword in text:
                if isinstance(value, int):
                    return reference_time + timedelta(days=value)
                elif value == "last_month":
                    # 上个月1号
                    if reference_time.month == 1:
                        return reference_time.replace(year=reference_time.year - 1, month=12, day=1)
                    return reference_time.replace(month=reference_time.month - 1, day=1)
                elif value == "this_month":
                    return reference_time.replace(day=1)
                elif value == "next_month":
                    if reference_time.month == 12:
                        return reference_time.replace(year=reference_time.year + 1, month=1, day=1)
                    return reference_time.replace(month=reference_time.month + 1, day=1)
                elif value == "last_year":
                    return reference_time.replace(year=reference_time.year - 1, month=1, day=1)
                elif value == "this_year":
                    return reference_time.replace(month=1, day=1)
                elif value == "next_year":
                    return reference_time.replace(year=reference_time.year + 1, month=1, day=1)

        return None

    @staticmethod
    def _extract_time(converted_text: str, original_text: str) -> Optional[Tuple[int, int]]:
        """从文本中提取时间（小时和分钟）"""
        # 时间匹配模式（按优先级排序）
        patterns = [
            r'(\d{1,2})点(\d{1,2})分?',     # 3点30、15点30分
            r'(\d{1,2})时(\d{1,2})分?',     # 3时30分、15时30（新支持）
            r'(\d{1,2}):(\d{2})',           # 15:30
            r'(\d{1,2})\.(\d{2})',          # 15.30
            r'(\d{1,2})点',                 # 6点、15点（无分钟）
            r'(\d{1,2})时',                 # 6时、15时（新支持）
        ]

        for pattern in patterns:
            match = re.search(pattern, converted_text)
            if match:
                hour = int(match.group(1))
                minute = int(match.group(2)) if len(match.groups()) > 1 and match.group(2) else 0

                # 使用 TIME_PERIODS 进行时间段调整
                for period_name, period_info in TimeParser.TIME_PERIODS.items():
                    if period_name in original_text:
                        adjust = period_info.get("adjust")
                        if adjust == "pm" and hour < 12:
                            hour += 12
                        elif adjust == "noon" and hour < 12:
                            hour = max(hour, 12)  # 中午至少12点
                        break

                # 验证时间范围
                if 0 <= hour <= 23 and 0 <= minute <= 59:
                    return (hour, minute)

        # 没有明确时间，检查是否只有时间段
        for period_name, period_info in TimeParser.TIME_PERIODS.items():
            if period_name in original_text:
                # 返回该时间段的默认小时
                return (period_info["default"], 0)

        # 特殊时间点处理
        if "子夜" in original_text:
            return (0, 0)
        if "黄昏" in original_text:
            return (18, 0)

        return None

    @staticmethod
    def format_time(dt: datetime) -> str:
        """格式化时间显示 - 始终显示具体日期"""
        weekdays = ["周一", "周二", "周三", "周四", "周五", "周六", "周日"]

        # 格式: 2月19日 周三 15:00
        return f"{dt.month}月{dt.day}日 {weekdays[dt.weekday()]} {dt.strftime('%H:%M')}"


# 便捷函数
def parse_time(time_str: str, reference_time: Optional[datetime] = None) -> Optional[datetime]:
    """解析时间字符串（便捷函数）"""
    return TimeParser.parse(time_str, reference_time)


def format_time(dt: datetime) -> str:
    """格式化时间显示（便捷函数）"""
    return TimeParser.format_time(dt)
