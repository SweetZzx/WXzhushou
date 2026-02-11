"""
日程助手服务 - 完全简化版本
只使用 GLM SDK，不依赖 LangChain
"""
from zai import ZhipuAiClient
from typing import List, Any, Optional
import logging
import json
import re

from services.schedule_service import ScheduleService
from utils.time_parser import parse_time

logger = logging.getLogger(__name__)


class ScheduleAgentService:
    """日程助手服务 - 直接使用 GLM Function Calling"""

    SYSTEM_PROMPT = """你是一个智能日程助手，可以帮助用户管理日程。

你的功能包括：
1. 📅 创建日程 - 记录用户安排的时间和事件
2. 🔍 查询日程 - 帮用户查看特定日期的安排
3. ✏️ 修改日程 - 更新已存在的日程信息
4. 🗑️ 删除日程 - 移除不需要的日程

请用中文回复。当用户需要操作日程时，调用相应的函数。

Function 定义：
- create_schedule: 创建日程，参数包括 title(标题)、datetime(时间)、description(描述)
- query_schedules: 查询日程，参数包括 date(日期)
- delete_schedule: 删除日程，参数包括 schedule_id(ID)
- update_schedule: 更新日程，参数包括 schedule_id(ID)、title(标题)或datetime(时间)

如果用户的消息不涉及日程操作，则进行友好的普通对话。"""

    FUNCTIONS = [
        {
            "type": "function",
            "function": {
                "name": "create_schedule",
                "description": "创建一个新的日程",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "title": {"type": "string", "description": "日程标题"},
                        "datetime": {"type": "string", "description": "日程时间，如：明天下午3点"},
                        "description": {"type": "string", "description": "详细描述"}
                    },
                    "required": ["title", "datetime"]
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "query_schedules",
                "description": "查询用户的日程",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "date": {"type": "string", "description": "查询日期，如：今天、明天"}
                    }
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "delete_schedule",
                "description": "删除日程",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "schedule_id": {"type": "integer", "description": "日程ID"}
                    },
                    "required": ["schedule_id"]
                }
            }
        }
    ]

    def __init__(self, zhipu_api_key: str, model: str = "glm-4"):
        self.api_key = zhipu_api_key
        self.model = model
        self.client = ZhipuAiClient(api_key=zhipu_api_key)
        logger.info("ScheduleAgentService 初始化成功")

    async def process(self, message: str, user_id: str, db_session) -> str:
        """处理用户消息"""
        try:
            schedule_service = ScheduleService(db_session)

            messages = [
                {"role": "system", "content": self.SYSTEM_PROMPT},
                {"role": "user", "content": message}
            ]

            response = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                tools=self.FUNCTIONS,
                temperature=0.7,
            )

            # 检查是否有工具调用
            if hasattr(response.choices[0].message, 'tool_calls') and response.choices[0].message.tool_calls:
                return await self._execute_tools(response.choices[0].message.tool_calls, schedule_service, user_id)

            return response.choices[0].message.content

        except Exception as e:
            logger.error(f"处理失败: {e}", exc_info=True)
            # 普通对话回退
            try:
                response = self.client.chat.completions.create(
                    model=self.model,
                    messages=[
                        {"role": "system", "content": "你是一个友好的AI助手。"},
                        {"role": "user", "content": message}
                    ]
                )
                return response.choices[0].message.content
            except:
                return "抱歉，服务暂时不可用。"

    async def _execute_tools(self, tool_calls, schedule_service, user_id):
        """执行工具调用"""
        results = []
        for tool_call in tool_calls:
            fn_name = tool_call.function.name
            fn_args = json.loads(tool_call.function.arguments)

            if fn_name == "create_schedule":
                result = await schedule_service.create_schedule(
                    user_id=user_id,
                    title=fn_args.get("title"),
                    time_str=fn_args.get("datetime"),
                    description=fn_args.get("description", "")
                )
                if result:
                    results.append(f"✅ 日程创建成功！\n{schedule_service.format_schedule(result)}")
                else:
                    results.append("❌ 创建失败，请检查时间格式")

            elif fn_name == "query_schedules":
                date = fn_args.get("date", "今天")
                schedules = await schedule_service.list_schedules(user_id, date)
                if schedules:
                    reply = f"📋 {date}的日程：\n\n"
                    for i, s in enumerate(schedules, 1):
                        reply += f"{i}. {schedule_service.format_schedule(s)}\n\n"
                    results.append(reply.strip())
                else:
                    results.append(f"📭 {date}没有日程安排")

            elif fn_name == "delete_schedule":
                success = await schedule_service.delete_schedule(fn_args.get("schedule_id"), user_id)
                results.append(f"✅ 已删除日程" if success else "❌ 删除失败")

        return "\n\n".join(results) if results else "操作完成"
