"""
日程助手服务 - 简化版本
直接使用 GLM Function Calling，不依赖 LangChain Agent
"""
from zai import ZhipuAiClient
from typing import List, Dict, Any, Optional
import logging
import json

from services.langchain_tools import create_schedule_tools
from services.schedule_service import ScheduleService

logger = logging.getLogger(__name__)


class ScheduleAgentService:
    """日程助手服务 - 使用 GLM Function Calling"""

    # 系统提示词
    SYSTEM_PROMPT = """你是一个智能日程助手，可以帮助用户管理日程。

你的功能包括：
1. 📅 创建日程 - 记录用户安排的时间和事件
2. 🔍 查询日程 - 帮用户查看特定日期的安排
3. ✏️ 修改日程 - 更新已存在的日程信息
4. 🗑️ 删除日程 - 移除不需要的日程

使用指南：
- 创建日程时，尽量获取完整信息（标题、时间、描述）
- 查询时，默认查询"今天"的日程
- 修改和删除前，确认日程ID是否正确
- 使用友好、简洁的语言与用户交流
- 操作成功后，简要确认结果

请用中文回复。当用户需要操作日程时，调用相应的函数。
"""

    # Function 定义
    FUNCTIONS = [
        {
            "type": "function",
            "function": {
                "name": "create_schedule",
                "description": "创建一个新的日程安排",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "title": {
                            "type": "string",
                            "description": "日程标题，如：开会、看病、健身"
                        },
                        "datetime": {
                            "type": "string",
                            "description": "日程时间，支持自然语言，如：明天下午3点、后天上午10点"
                        },
                        "description": {
                            "type": "string",
                            "description": "日程的详细描述"
                        },
                        "remind_before": {
                            "type": "integer",
                            "description": "提前多少分钟提醒"
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
                "description": "查询用户的日程列表",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "date": {
                            "type": "string",
                            "description": "查询日期，如：今天、明天、本周、下周"
                        }
                    }
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "delete_schedule",
                "description": "删除指定的日程",
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
                "name": "update_schedule",
                "description": "更新日程信息",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "schedule_id": {
                            "type": "integer",
                            "description": "要更新的日程ID"
                        },
                        "title": {
                            "type": "string",
                            "description": "新的日程标题"
                        },
                        "datetime": {
                            "type": "string",
                            "description": "新的日程时间"
                        }
                    },
                    "required": ["schedule_id"]
                }
            }
        }
    ]

    def __init__(self, zhipu_api_key: str, model: str = "glm-4"):
        """
        初始化服务

        Args:
            zhipu_api_key: 智谱AI API密钥
            model: 模型名称
        """
        self.api_key = zhipu_api_key
        self.model = model
        self.client = ZhipuAiClient(api_key=zhipu_api_key)
        logger.info("ScheduleAgentService 初始化成功")

    async def process(
        self,
        message: str,
        user_id: str,
        db_session
    ) -> str:
        """
        处理用户消息

        Args:
            message: 用户消息
            user_id: 用户ID
            db_session: 数据库会话

        Returns:
            AI 回复
        """
        try:
            # 创建日程服务
            schedule_service = ScheduleService(db_session)

            # 调用 GLM API
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
            if response.choices[0].message.tool_calls:
                # 执行工具调用
                return await self._execute_tool_calls(
                    response.choices[0].message.tool_calls,
                    schedule_service,
                    user_id
                )
            else:
                # 普通对话回复
                return response.choices[0].message.content

        except Exception as e:
            logger.error(f"处理失败: {e}", exc_info=True)
            # 回退到普通对话
            try:
                response = self.client.chat.completions.create(
                    model=self.model,
                    messages=[
                        {"role": "system", "content": "你是一个友好的AI助手。"},
                        {"role": "user", "content": message}
                    ],
                    temperature=0.7,
                )
                return response.choices[0].message.content
            except Exception as e2:
                logger.error(f"回退对话也失败: {e2}")
                return "抱歉，服务暂时不可用，请稍后再试。"

    async def _execute_tool_calls(
        self,
        tool_calls: List[Any],
        schedule_service: ScheduleService,
        user_id: str
    ) -> str:
        """执行工具调用"""
        results = []

        for tool_call in tool_calls:
            function_name = tool_call.function.name
            function_args = json.loads(tool_call.function.arguments)

            if function_name == "create_schedule":
                result = await schedule_service.create_schedule(
                    user_id=user_id,
                    title=function_args.get("title"),
                    time_str=function_args.get("datetime"),
                    description=function_args.get("description", ""),
                    remind_before=function_args.get("remind_before", 0)
                )
                results.append(result)

            elif function_name == "query_schedules":
                date = function_args.get("date", "今天")
                schedules = await schedule_service.list_schedules(user_id, date)
                if not schedules:
                    results.append(f"📭 {date}没有日程安排。")
                else:
                    result = f"📋 {date}的日程：\n\n"
                    for i, schedule in enumerate(schedules, 1):
                        result += f"{i}. {schedule_service.format_schedule(schedule)}\n\n"
                    results.append(result.strip())

            elif function_name == "delete_schedule":
                success = await schedule_service.delete_schedule(
                    function_args.get("schedule_id"),
                    user_id
                )
                if success:
                    results.append(f"✅ 已删除日程 (ID: {function_args.get('schedule_id')})")
                else:
                    results.append(f"❌ 删除失败，未找到日程 (ID: {function_args.get('schedule_id')})")

            elif function_name == "update_schedule":
                result = await schedule_service.update_schedule(
                    schedule_id=function_args.get("schedule_id"),
                    user_id=user_id,
                    title=function_args.get("title"),
                    time_str=function_args.get("datetime")
                )
                if result:
                    results.append(f"✅ 日程更新成功！\n{schedule_service.format_schedule(result)}")
                else:
                    results.append(f"❌ 更新失败 (ID: {function_args.get('schedule_id')})")

        return "\n\n".join(results)

    async def chat(self, message: str, user_id: str) -> str:
        """普通对话"""
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "你是一个友好的AI助手。"},
                    {"role": "user", "content": message}
                ],
                temperature=0.7,
            )
            return response.choices[0].message.content
        except Exception as e:
            logger.error(f"对话失败: {e}")
            return f"抱歉，AI 回复出错：{str(e)}"
