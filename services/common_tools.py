"""
通用工具定义
提供日期、时间等常用查询工具
"""
from langchain.tools import tool
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)


def get_common_tools():
    """
    创建通用工具集

    Returns:
        LangChain 工具列表
    """

    @tool
    def get_current_time() -> str:
        """
        【时间查询工具】获取当前的日期和时间。

        当用户询问以下问题时使用：
        - "现在几点了？"
        - "今天几号？"
        - "现在是哪一年？"
        - "今天星期几？"
        - "现在是什么时间？"

        Returns:
            当前日期和时间的详细信息
        """
        now = datetime.now()
        weekdays = ["星期一", "星期二", "星期三", "星期四", "星期五", "星期六", "星期日"]

        return f"""当前时间信息：
日期：{now.strftime('%Y年%m月%d日')}
时间：{now.strftime('%H:%M:%S')}
星期：{weekdays[now.weekday()]}
时区：中国标准时间 (UTC+8)"""

    @tool
    def get_date_info(date_str: str = "今天") -> str:
        """
        【日期查询工具】获取指定日期的详细信息。

        当用户询问以下问题时使用：
        - "明天是几号？"
        - "下周一是哪天？"
        - "这个月有多少天？"
        - "2024年2月有多少天？"

        Args:
            date_str: 要查询的日期，如：今天、明天、后天、下周、下个月

        Returns:
            指定日期的详细信息
        """
        now = datetime.now()
        weekdays = ["星期一", "星期二", "星期三", "星期四", "星期五", "星期六", "星期日"]

        # 解析日期
        if date_str in ["今天", "今日"]:
            target = now
        elif date_str in ["明天", "明日"]:
            target = now + timedelta(days=1)
        elif date_str in ["后天"]:
            target = now + timedelta(days=2)
        elif date_str in ["大后天"]:
            target = now + timedelta(days=3)
        elif date_str in ["昨天", "昨日"]:
            target = now - timedelta(days=1)
        elif date_str in ["前天"]:
            target = now - timedelta(days=2)
        elif "下周" in date_str:
            # 下周X
            days_ahead = 7 + (0 if "一" in date_str else
                              1 if "二" in date_str else
                              2 if "三" in date_str else
                              3 if "四" in date_str else
                              4 if "五" in date_str else
                              5 if "六" in date_str else 6)
            days_since_monday = now.weekday()
            target = now + timedelta(days=(7 - days_since_monday + days_ahead))
        elif "这周" in date_str or "本周" in date_str:
            # 这周X
            weekday_num = (0 if "一" in date_str else
                          1 if "二" in date_str else
                          2 if "三" in date_str else
                          3 if "四" in date_str else
                          4 if "五" in date_str else
                          5 if "六" in date_str else 6)
            days_since_monday = now.weekday()
            target = now + timedelta(days=(weekday_num - days_since_monday))
        else:
            return f"无法识别的日期格式：{date_str}，请使用：今天、明天、后天、下周X等格式"

        # 计算距离今天的天数
        days_diff = (target.date() - now.date()).days
        if days_diff == 0:
            diff_str = "今天"
        elif days_diff == 1:
            diff_str = "明天（距今1天）"
        elif days_diff == -1:
            diff_str = "昨天（距今-1天）"
        elif days_diff > 0:
            diff_str = f"距今{days_diff}天"
        else:
            diff_str = f"距今{days_diff}天"

        # 获取该月天数
        if target.month == 12:
            days_in_month = 31
        else:
            next_month = target.replace(month=target.month + 1, day=1)
            last_day = next_month - timedelta(days=1)
            days_in_month = last_day.day

        return f"""日期信息：
日期：{target.strftime('%Y年%m月%d日')}
星期：{weekdays[target.weekday()]}
{diff_str}
当月天数：{days_in_month}天"""

    @tool
    def calculate_days(start_date: str, end_date: str = "今天") -> str:
        """
        【日期计算工具】计算两个日期之间相差的天数。

        当用户询问以下问题时使用：
        - "距离春节还有多少天？"
        - "从今天到下个月有多少天？"
        - "2024年有多少天？"

        Args:
            start_date: 开始日期，如：今天、2024-01-01
            end_date: 结束日期，如：今天、2024-12-31

        Returns:
            日期差计算结果
        """
        now = datetime.now()

        def parse_simple_date(date_str):
            """简单日期解析"""
            if date_str in ["今天", "今日"]:
                return now.date()
            elif date_str in ["明天", "明日"]:
                return (now + timedelta(days=1)).date()
            elif date_str in ["昨天"]:
                return (now - timedelta(days=1)).date()
            else:
                # 尝试解析 YYYY-MM-DD 格式
                try:
                    return datetime.strptime(date_str, "%Y-%m-%d").date()
                except:
                    try:
                        return datetime.strptime(date_str, "%Y年%m月%d日").date()
                    except:
                        return None

        start = parse_simple_date(start_date)
        end = parse_simple_date(end_date)

        if not start:
            return f"无法解析开始日期：{start_date}，请使用：今天、明天、YYYY-MM-DD 等格式"
        if not end:
            return f"无法解析结束日期：{end_date}，请使用：今天、明天、YYYY-MM-DD 等格式"

        days_diff = (end - start).days

        if days_diff >= 0:
            return f"从 {start} 到 {end} 相差 {days_diff} 天"
        else:
            return f"从 {start} 到 {end} 相差 {abs(days_diff)} 天（已过去）"

    return [get_current_time, get_date_info, calculate_days]
