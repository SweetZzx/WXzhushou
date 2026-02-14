"""
Agent 服务
使用智谱 zhipuai SDK 实现 Agent 功能
"""
from zhipuai import ZhipuAI
import json
import logging
from datetime import datetime, timedelta

from services.schedule_service import ScheduleService

logger = logging.getLogger(__name__)


class ScheduleAgentService:
    """AI 助手服务 - 支持日常对话和日程管理"""

    # 系统提示词
    SYSTEM_PROMPT = """你是一个友好、智能的AI助手。

【核心定位】
- 你首先是一个可以回答各种问题的AI助手
- 你还具备日程管理的额外能力

【⚠️ 创建日程的正确流程 - 必须严格遵守】
1. 用户说要添加日程时，先调用 parse_time_to_iso 将用户说的时间转换为ISO格式
2. 等待返回的ISO格式时间（如 "2026-02-14 15:00"）
3. 使用返回的ISO时间调用 create_schedule

【示例对话流程】
用户：添加日程，后天晚上十点睡觉
AI内心：需要先解析时间
AI调用：parse_time_to_iso(natural_time="后天晚上十点")
系统返回：2026-02-15 22:00
AI调用：create_schedule(title="睡觉", datetime="2026-02-15 22:00")

【⚠️ 修改日程的正确流程】
1. 用户说修改日程但不知道ID时：
   - 如果用户提到标题关键词，调用 find_schedule_by_keyword 搜索
   - 如果用户只说"我的日程"或没明确指向，调用 list_all_schedules 显示列表

2. 用户说"提前/推迟 X 分钟/小时/天"时：
   - 使用 shift_schedule_time 工具，计算偏移分钟数
   - 提前30分钟 = shift_minutes=-30，推迟1小时 = shift_minutes=60，推迟1天 = shift_minutes=1440

3. 用户要改具体时间时：
   - 先调用 parse_time_to_iso 解析新时间
   - 再调用 update_schedule

【工具列表】
日程管理：
- parse_time_to_iso: 解析自然语言时间 → 返回 YYYY-MM-DD HH:MM
- create_schedule: 创建日程（datetime 必须是 ISO 格式）
- query_schedules: 查询日程（date 用 今天/明天/后天）
- list_all_schedules: 列出所有日程
- find_schedule_by_keyword: 通过标题关键词搜索日程
- update_schedule: 修改日程（标题/时间/备注）
- shift_schedule_time: 偏移日程时间（提前/推迟）
- delete_schedule: 删除日程

提醒设置：
- get_reminder_settings: 获取提醒设置
- update_reminder_settings: 修改提醒设置

【⚠️ 禁止事项】
- 禁止直接将自然语言传给 create_schedule/update_schedule 的 datetime 参数
- 禁止自己猜测日期，必须调用 parse_time_to_iso 获取准确时间

【重要】
- 闲聊、问候、知识问答等不调用工具，直接对话
- 请用中文回复
- 回复简洁友好"""

    def __init__(self, zhipu_api_key: str, model: str = "glm-4"):
        """
        初始化 Agent 服务

        Args:
            zhipu_api_key: 智谱AI API密钥
            model: 模型名称
        """
        self.api_key = zhipu_api_key
        self.model = model

        # 使用智谱 zhipuai SDK
        self.client = ZhipuAI(api_key=zhipu_api_key)

        logger.info(f"ScheduleAgentService 初始化成功，使用模型: {model}")

    def _build_tools(self) -> list:
        """构建工具定义"""
        return [
            {
                "type": "function",
                "function": {
                    "name": "get_current_datetime",
                    "description": "获取当前的日期和时间（ISO格式）。在处理任何涉及时间的请求前，必须先调用此函数获取当前时间作为参考。",
                    "parameters": {
                        "type": "object",
                        "properties": {},
                        "required": []
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "get_current_time",
                    "description": "获取当前的日期和时间。当用户询问现在几点、今天几号、今天星期几时使用。",
                    "parameters": {
                        "type": "object",
                        "properties": {},
                        "required": []
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "parse_time_to_iso",
                    "description": "将自然语言时间转换为ISO格式。创建或修改日程前，必须先调用此函数将用户说的时间转换为YYYY-MM-DD HH:MM格式。",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "natural_time": {
                                "type": "string",
                                "description": "用户说的自然语言时间，如：明天下午三点、后天晚上十点、周五上午9点"
                            }
                        },
                        "required": ["natural_time"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "get_date_info",
                    "description": "获取指定日期的详细信息。当用户询问明天是几号、下周一是哪天时使用。",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "date_str": {
                                "type": "string",
                                "description": "要查询的日期，如：今天、明天、后天"
                            }
                        },
                        "required": ["date_str"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "create_schedule",
                    "description": "创建新日程。⚠️调用前必须先调用parse_time_to_iso获取ISO格式的时间！datetime参数只接受YYYY-MM-DD HH:MM格式。",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "title": {
                                "type": "string",
                                "description": "日程标题，如：开会、看病、健身"
                            },
                            "datetime": {
                                "type": "string",
                                "description": "日程时间。⚠️必须是精确格式YYYY-MM-DD HH:MM，如2026-02-14 09:00。禁止传入'明天下午三点'等自然语言！必须先获取当前时间再计算具体日期。"
                            },
                            "description": {
                                "type": "string",
                                "description": "日程的详细描述（可选）"
                            }
                        },
                        "required": ["title", "datetime"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "query_schedules",
                    "description": "查询指定日期的日程。当用户想查看某天的安排时使用。注意：必须准确传递用户说的日期！",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "date": {
                                "type": "string",
                                "description": "查询日期。必须准确传递用户指定的值：如果用户说'明天'就传'明天'，说'今天'就传'今天'。可选值：今天、明天、后天、本周、下周"
                            }
                        },
                        "required": ["date"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "list_all_schedules",
                    "description": "列出用户的所有日程（带ID）。当用户想看所有日程、或需要知道日程ID以便修改/删除时使用。",
                    "parameters": {
                        "type": "object",
                        "properties": {},
                        "required": []
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "update_schedule",
                    "description": "修改已有日程。需要日程ID，如果用户不知道ID，先调用 find_schedule_by_keyword 或 list_all_schedules。datetime参数必须是YYYY-MM-DD HH:MM格式。",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "schedule_id": {
                                "type": "integer",
                                "description": "要修改的日程ID"
                            },
                            "title": {
                                "type": "string",
                                "description": "新的日程标题（可选）"
                            },
                            "datetime": {
                                "type": "string",
                                "description": "新的日程时间，必须是YYYY-MM-DD HH:MM格式（可选）"
                            },
                            "description": {
                                "type": "string",
                                "description": "新的备注内容（可选）"
                            }
                        },
                        "required": ["schedule_id"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "find_schedule_by_keyword",
                    "description": "通过标题关键词搜索日程。当用户说'把开会那个日程改一下'、'修改健身的日程'等通过标题描述日程时使用。",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "keyword": {
                                "type": "string",
                                "description": "日程标题中的关键词，如：开会、健身、睡觉"
                            },
                            "date": {
                                "type": "string",
                                "description": "日期筛选（可选）：今天、明天、后天"
                            }
                        },
                        "required": ["keyword"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "shift_schedule_time",
                    "description": "偏移日程时间（提前或推迟）。当用户说'提前30分钟'、'推迟1小时'、'往后推一天'时使用。",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "schedule_id": {
                                "type": "integer",
                                "description": "日程ID"
                            },
                            "shift_minutes": {
                                "type": "integer",
                                "description": "偏移分钟数。正数=推迟，负数=提前。如：提前30分钟=-30，推迟1小时=60，推迟1天=1440"
                            }
                        },
                        "required": ["schedule_id", "shift_minutes"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "delete_schedule",
                    "description": "删除日程。需要日程ID，如果用户不知道ID，先调用 list_all_schedules。",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "schedule_id": {
                                "type": "integer",
                                "description": "要删除的日程ID"
                            }
                        },
                        "required": ["schedule_id"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "get_reminder_settings",
                    "description": "获取用户的提醒设置。当用户询问提醒相关设置时使用。",
                    "parameters": {
                        "type": "object",
                        "properties": {},
                        "required": []
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "update_reminder_settings",
                    "description": "更新用户的提醒设置。当用户想修改提醒开关或时间时使用。",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "daily_reminder_enabled": {
                                "type": "boolean",
                                "description": "是否开启每日日程提醒（true/false）"
                            },
                            "daily_reminder_time": {
                                "type": "string",
                                "description": "每日提醒时间，格式：HH:MM，如 08:00"
                            },
                            "pre_schedule_reminder_enabled": {
                                "type": "boolean",
                                "description": "是否开启日程开始前提醒（true/false）"
                            },
                            "pre_schedule_reminder_minutes": {
                                "type": "integer",
                                "description": "日程开始前多少分钟提醒，如 10、15、30"
                            }
                        },
                        "required": []
                    }
                }
            }
        ]

    async def _execute_tool(self, tool_name: str, tool_args: dict,
                           schedule_service: ScheduleService, user_id: str) -> str:
        """执行工具函数"""
        now = datetime.now()
        weekdays = ["星期一", "星期二", "星期三", "星期四", "星期五", "星期六", "星期日"]

        if tool_name == "get_current_datetime":
            # 返回ISO格式的时间供AI计算日期使用
            return f"当前时间（ISO格式）：{now.strftime('%Y-%m-%d %H:%M:%S')}\n日期：{now.strftime('%Y年%m月%d日')}\n星期：{weekdays[now.weekday()]}\n\n请根据此时间计算用户指定的日期，输出格式为 YYYY-MM-DD HH:MM"

        if tool_name == "get_current_time":
            return f"当前时间信息：\n日期：{now.strftime('%Y年%m月%d日')}\n时间：{now.strftime('%H:%M:%S')}\n星期：{weekdays[now.weekday()]}"

        elif tool_name == "parse_time_to_iso":
            natural_time = tool_args.get("natural_time", "")
            logger.info(f"解析自然语言时间: '{natural_time}'")
            from utils.time_parser import parse_time
            parsed_time = parse_time(natural_time, now)
            if parsed_time:
                iso_time = parsed_time.strftime("%Y-%m-%d %H:%M")
                logger.info(f"解析结果: '{natural_time}' -> {iso_time}")
                return f"时间解析结果：{iso_time}\n请使用这个ISO格式时间调用create_schedule。"
            else:
                return f"无法解析时间：{natural_time}，请让用户更明确地说明时间。"

        elif tool_name == "get_date_info":
            date_str = tool_args.get("date_str", "今天")
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
            diff_str = "今天" if days_diff == 0 else f"距今{days_diff}天"
            return f"日期信息：\n日期：{target.strftime('%Y年%m月%d日')}\n星期：{weekdays[target.weekday()]}\n{diff_str}"

        elif tool_name == "create_schedule":
            title = tool_args.get("title", "")
            datetime_str = tool_args.get("datetime", "")
            description = tool_args.get("description", "")
            logger.info(f"创建日程参数: title={title}, datetime={datetime_str}, description={description}")
            schedule = await schedule_service.create_schedule(
                user_id=user_id,
                title=title,
                time_str=datetime_str,
                description=description or None
            )
            if schedule:
                return f"日程创建成功！\n{schedule_service.format_schedule(schedule)}"
            return "创建日程失败，请检查时间格式是否正确。"

        elif tool_name == "query_schedules":
            date = tool_args.get("date", "今天")
            schedules = await schedule_service.list_schedules(user_id=user_id, date_str=date)
            if not schedules:
                return f"{date}没有日程安排。"
            result = f"📅 {date}的日程：\n\n"
            for i, schedule in enumerate(schedules, 1):
                result += f"{i}. {schedule_service.format_schedule(schedule)}\n\n"
            return result.strip()

        elif tool_name == "list_all_schedules":
            # 获取所有日程（最近7天）
            all_schedules = []
            for day_offset in range(7):
                date_str = "今天" if day_offset == 0 else f"{day_offset}天后"
                if day_offset == 1:
                    date_str = "明天"
                elif day_offset == 2:
                    date_str = "后天"
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

        elif tool_name == "update_schedule":
            schedule_id = tool_args.get("schedule_id")
            title = tool_args.get("title")
            datetime_str = tool_args.get("datetime")
            description = tool_args.get("description")
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

        elif tool_name == "find_schedule_by_keyword":
            keyword = tool_args.get("keyword", "")
            date = tool_args.get("date")
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

        elif tool_name == "shift_schedule_time":
            schedule_id = tool_args.get("schedule_id")
            shift_minutes = tool_args.get("shift_minutes")
            schedule = await schedule_service.shift_schedule_time(
                schedule_id=schedule_id,
                user_id=user_id,
                shift_minutes=shift_minutes
            )
            if schedule:
                direction = "推迟" if shift_minutes > 0 else "提前"
                abs_minutes = abs(shift_minutes)
                if abs_minutes >= 1440:
                    time_desc = f"{abs_minutes // 1440}天"
                elif abs_minutes >= 60:
                    time_desc = f"{abs_minutes // 60}小时"
                else:
                    time_desc = f"{abs_minutes}分钟"
                return f"已{direction}{time_desc}！\n{schedule_service.format_schedule(schedule)}"
            return f"时间调整失败，未找到日程或调整后时间已过 (ID: {schedule_id})"

        elif tool_name == "delete_schedule":
            schedule_id = tool_args.get("schedule_id")
            success = await schedule_service.delete_schedule(schedule_id, user_id)
            if success:
                return f"已删除日程 (ID: {schedule_id})"
            return f"删除失败，未找到日程或无权操作 (ID: {schedule_id})"

        elif tool_name == "get_reminder_settings":
            from services.reminder_service import reminder_service
            settings = await reminder_service.get_user_settings(user_id)
            if settings:
                daily_status = "已开启" if settings["daily_reminder_enabled"] else "已关闭"
                pre_status = "已开启" if settings["pre_schedule_reminder_enabled"] else "已关闭"
                return (f"⏰ 您的提醒设置：\n\n"
                       f"📅 每日日程提醒：{daily_status}\n"
                       f"   - 提醒时间：{settings['daily_reminder_time']}\n\n"
                       f"🔔 日程开始前提醒：{pre_status}\n"
                       f"   - 提前 {settings['pre_schedule_reminder_minutes']} 分钟提醒")
            return "获取提醒设置失败。"

        elif tool_name == "update_reminder_settings":
            from services.reminder_service import reminder_service
            settings = await reminder_service.update_user_settings(
                user_id=user_id,
                daily_reminder_enabled=tool_args.get("daily_reminder_enabled"),
                daily_reminder_time=tool_args.get("daily_reminder_time"),
                pre_schedule_reminder_enabled=tool_args.get("pre_schedule_reminder_enabled"),
                pre_schedule_reminder_minutes=tool_args.get("pre_schedule_reminder_minutes")
            )
            if settings:
                daily_status = "已开启" if settings.daily_reminder_enabled else "已关闭"
                pre_status = "已开启" if settings.pre_schedule_reminder_enabled else "已关闭"
                return (f"✅ 提醒设置已更新！\n\n"
                       f"📅 每日日程提醒：{daily_status}（{settings.daily_reminder_time}）\n"
                       f"🔔 日程开始前提醒：{pre_status}（提前 {settings.pre_schedule_reminder_minutes} 分钟）")
            return "更新提醒设置失败。"

        return f"未知工具: {tool_name}"

    async def process(self, message: str, user_id: str, db_session) -> str:
        """处理用户消息"""
        try:
            schedule_service = ScheduleService(db_session)
            tools = self._build_tools()
            messages = [
                {"role": "system", "content": self.SYSTEM_PROMPT},
                {"role": "user", "content": message}
            ]

            max_iterations = 5
            for _ in range(max_iterations):
                response = self.client.chat.completions.create(
                    model=self.model,
                    messages=messages,
                    tools=tools,
                    tool_choice="auto",
                    temperature=0.7
                )

                assistant_message = response.choices[0].message

                if not hasattr(assistant_message, 'tool_calls') or not assistant_message.tool_calls:
                    content = assistant_message.content or "抱歉，我没有理解您的问题。"
                    return content.strip()

                messages.append({
                    "role": "assistant",
                    "content": assistant_message.content or "",
                    "tool_calls": [
                        {
                            "id": tc.id,
                            "type": "function",
                            "function": {
                                "name": tc.function.name,
                                "arguments": tc.function.arguments
                            }
                        }
                        for tc in assistant_message.tool_calls
                    ]
                })

                for tool_call in assistant_message.tool_calls:
                    function_name = tool_call.function.name
                    function_args = json.loads(tool_call.function.arguments)
                    logger.info(f"执行工具: {function_name}, 参数: {function_args}")

                    result = await self._execute_tool(
                        function_name, function_args, schedule_service, user_id
                    )

                    messages.append({
                        "role": "tool",
                        "tool_call_id": tool_call.id,
                        "content": result
                    })

            return "抱歉，处理您的请求时超出了最大迭代次数。"

        except Exception as e:
            logger.error(f"Agent 处理失败: {e}", exc_info=True)
            return f"抱歉，处理请求时出错：{str(e)}"

    async def chat(self, message: str, user_id: str) -> str:
        """普通对话"""
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "你是一个友好的AI助手，请用中文回复。"},
                    {"role": "user", "content": message}
                ],
                temperature=0.7
            )
            return response.choices[0].message.content
        except Exception as e:
            logger.error(f"对话失败: {e}", exc_info=True)
            return f"抱歉，AI 回复出错：{str(e)}"


async def process_schedule_request(message: str, user_id: str, db_session, api_key: str) -> str:
    """处理日程请求（便捷函数）"""
    agent = ScheduleAgentService(api_key)
    return await agent.process(message, user_id, db_session)
