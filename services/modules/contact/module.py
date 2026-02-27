"""
联系人模块实现
"""
import logging
from typing import Type

from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from services.modules.base import BaseModule
from services.chat_with_action import ContactAction
from services.modules.contact.service import ContactService

logger = logging.getLogger(__name__)

# 联系人模块的 SYSTEM_PROMPT 片段
CONTACT_PROMPT = """
【联系人意图判断】
只要消息提到某人的信息（电话、生日、爱好、QQ、邮箱、地址等），就应该创建/更新联系人：
- "小明的电话是13812345678" → type: "contact_create", name: "小明", phone: "13812345678"
- "小明生日是3月15号" → type: "contact_create", name: "小明", birthday: "03-15"
- "小明喜欢打篮球" → type: "contact_create", name: "小明", extra: "爱好：打篮球"
- "小明的电话是多少" → type: "contact_query", name: "小明", query_field: "phone"
- "小明的电话" → type: "contact_query", name: "小明", query_field: "phone"
- "小明的生日是什么时候" → type: "contact_query", name: "小明", query_field: "birthday"
- "小明的生日" → type: "contact_query", name: "小明", query_field: "birthday"
- "小明的所有信息" → type: "contact_query", name: "小明", query_field: "all"
- "我记录了哪些联系人" → type: "contact_query"（不填name）
"""


class ContactModule(BaseModule):
    """联系人管理模块"""

    module_id: str = "contact"
    module_name: str = "联系人管理"
    module_description: str = "管理你的联系人信息，支持记录和查询电话、生日等"

    @property
    def action_model(self) -> Type[BaseModel]:
        return ContactAction

    async def execute(
        self,
        action: BaseModel,
        user_id: str,
        db_session: AsyncSession
    ) -> str:
        """执行联系人操作"""
        if not isinstance(action, ContactAction):
            return "联系人操作格式错误"

        contact_service = ContactService(db_session)
        action_type = action.type

        if action_type == "contact_create":
            return await self._handle_create(action, user_id, contact_service)
        elif action_type == "contact_query":
            return await self._handle_query(action, user_id, contact_service)
        elif action_type == "contact_delete":
            return await self._handle_delete(action, user_id, contact_service)
        else:
            return "未知的联系人操作"

    def get_prompt_section(self) -> str:
        return CONTACT_PROMPT

    async def _handle_create(
        self,
        action: ContactAction,
        user_id: str,
        contact_service: ContactService
    ) -> str:
        """创建或更新联系人"""
        if not action.name:
            return "请告诉我联系人的姓名"

        try:
            logger.info(f"[联系人创建] name={action.name}, phone={action.phone}, birthday={action.birthday}")

            contact, is_new = await contact_service.upsert_contact(
                user_id=user_id,
                name=action.name,
                phone=action.phone,
                birthday=action.birthday,
                remark=action.remark,
                extra=action.extra
            )

            logger.info(f"[联系人创建] 结果: id={contact.id}, is_new={is_new}, birthday={contact.birthday}")

            if is_new:
                reply = f"已添加联系人：{contact.name}"
            else:
                reply = f"已更新联系人：{contact.name}"

            info_parts = []
            if contact.phone:
                phone = contact_service.get_decrypted_phone(contact)
                info_parts.append(f"电话: {phone}")
            if contact.birthday:
                info_parts.append(f"生日: {contact.birthday}")
            if contact.remark:
                info_parts.append(f"备注: {contact.remark}")
            if contact.extra:
                info_parts.append(f"其他: {contact.extra}")

            if info_parts:
                reply += "\n" + "\n".join(info_parts)

            return reply

        except Exception as e:
            logger.error(f"创建联系人失败: {e}", exc_info=True)
            return "添加联系人失败，请稍后重试"

    async def _handle_query(
        self,
        action: ContactAction,
        user_id: str,
        contact_service: ContactService
    ) -> str:
        """查询联系人"""
        try:
            if action.name:
                clean_name = action.name.rstrip("的")
                logger.info(f"[联系人查询] 原始名称: {action.name}, 清理后: {clean_name}, 查询字段: {action.query_field}")

                contact = await contact_service.find_by_name(user_id, action.name)
                if not contact and clean_name != action.name:
                    contact = await contact_service.find_by_name(user_id, clean_name)

                if not contact:
                    name = clean_name or action.name
                    return f"没有找到「{name}」的联系方式，你可以说「{name}的电话是xxx」来添加"

                logger.info(f"[联系人查询] 找到联系人: id={contact.id}, name={contact.name}, birthday={contact.birthday}")

                query_field = action.query_field or ""

                if query_field == "phone":
                    if contact.phone:
                        phone = contact_service.get_decrypted_phone(contact)
                        return f"{contact.name}的电话是{phone}"
                    else:
                        return f"还没有记录{contact.name}的电话，你可以说「{contact.name}的电话是xxx」来添加"

                elif query_field == "birthday":
                    if contact.birthday:
                        return f"{contact.name}的生日是{contact.birthday}"
                    else:
                        return f"还没有记录{contact.name}的生日，你可以说「{contact.name}的生日是xx月xx日」来添加"

                else:
                    info_parts = []
                    if contact.phone:
                        phone = contact_service.get_decrypted_phone(contact)
                        info_parts.append(f"电话: {phone}")
                    if contact.birthday:
                        info_parts.append(f"生日: {contact.birthday}")
                    if contact.remark:
                        info_parts.append(f"备注: {contact.remark}")
                    if contact.extra:
                        info_parts.append(f"其他: {contact.extra}")

                    if info_parts:
                        reply = f"{contact.name}的信息：\n" + "\n".join(info_parts)
                    else:
                        reply = f"还没有记录{contact.name}的详细信息，你可以说「{contact.name}的电话是xxx」来添加"

                    return reply

            else:
                contacts = await contact_service.list_contacts(user_id)

                if not contacts:
                    return "还没有记录任何联系人，你可以说「小明的电话是xxx」来添加"

                if len(contacts) == 1:
                    c = contacts[0]
                    return f"你记录了1个联系人：{c.name}"

                reply = f"你记录了{len(contacts)}个联系人：\n"
                for i, c in enumerate(contacts, 1):
                    reply += f"\n{i}. {c.name}"
                    if c.birthday:
                        reply += f"（生日: {c.birthday}）"

                return reply

        except Exception as e:
            logger.error(f"查询联系人失败: {e}", exc_info=True)
            return "查询失败，请稍后重试"

    async def _handle_delete(
        self,
        action: ContactAction,
        user_id: str,
        contact_service: ContactService
    ) -> str:
        """删除联系人"""
        if not action.name:
            return "请告诉我要删除哪个联系人"

        try:
            contact = await contact_service.find_by_name(user_id, action.name)
            if not contact:
                return f"没有找到「{action.name}」"

            success = await contact_service.delete_contact(contact.id, user_id)

            if success:
                return f"已删除联系人：{action.name}"
            else:
                return "删除失败"

        except Exception as e:
            logger.error(f"删除联系人失败: {e}", exc_info=True)
            return "删除失败，请稍后重试"


# 创建模块实例
contact_module = ContactModule()
