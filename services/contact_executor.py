"""
联系人执行器
根据 LLM 提取的结构化数据执行联系人操作
"""
import logging
from typing import Optional

from services.contact_service import ContactService
from services.chat_with_action import ContactAction

logger = logging.getLogger(__name__)


class ContactExecutor:
    """联系人执行器"""

    async def process(
        self,
        action: ContactAction,
        user_id: str,
        db_session
    ) -> str:
        """
        处理联系人操作

        Args:
            action: 联系人操作
            user_id: 用户ID
            db_session: 数据库会话

        Returns:
            回复内容
        """
        contact_service = ContactService(db_session)

        if action.type == "contact_create":
            return await self._handle_create(action, user_id, contact_service)
        elif action.type == "contact_query":
            return await self._handle_query(action, user_id, contact_service)
        elif action.type == "contact_delete":
            return await self._handle_delete(action, user_id, contact_service)
        else:
            return "❓ 未知的联系人操作"

    async def _handle_create(
        self,
        action: ContactAction,
        user_id: str,
        contact_service: ContactService
    ) -> str:
        """创建或更新联系人"""
        if not action.name:
            return "❓ 请告诉我联系人的姓名"

        try:
            # 智能创建/更新
            contact, is_new = await contact_service.upsert_contact(
                user_id=user_id,
                name=action.name,
                phone=action.phone,
                birthday=action.birthday,
                remark=action.remark,
                extra=action.extra
            )

            # 构建回复
            if is_new:
                reply = f"✅ 已添加联系人：{contact.name}"
            else:
                reply = f"✅ 已更新联系人：{contact.name}"

            # 显示当前信息
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
                reply += "\n\n" + "\n".join(info_parts)

            return reply

        except Exception as e:
            logger.error(f"创建联系人失败: {e}", exc_info=True)
            return "❌ 添加联系人失败，请稍后重试"

    async def _handle_query(
        self,
        action: ContactAction,
        user_id: str,
        contact_service: ContactService
    ) -> str:
        """查询联系人"""
        try:
            if action.name:
                # 查询单个联系人
                contact = await contact_service.find_by_name(user_id, action.name)

                if not contact:
                    return f"🔍 没有找到「{action.name}」的联系方式\n💡 你可以说「{action.name}的电话是xxx」来添加"

                # 显示联系人信息
                reply = f"👤 {contact.name}"
                info_parts = []

                if contact.phone:
                    phone = contact_service.get_decrypted_phone(contact)
                    info_parts.append(f"📞 {phone}")
                if contact.birthday:
                    info_parts.append(f"🎂 {contact.birthday}")
                if contact.remark:
                    info_parts.append(f"📝 {contact.remark}")
                if contact.extra:
                    info_parts.append(f"📋 {contact.extra}")

                if info_parts:
                    reply += "\n\n" + "\n".join(info_parts)
                else:
                    reply += "\n\n💡 暂无详细信息，可以说「{action.name}的电话是xxx」来添加"

                return reply

            else:
                # 列出所有联系人
                contacts = await contact_service.list_contacts(user_id)

                if not contacts:
                    return "📭 还没有记录任何联系人\n💡 你可以说「小明的电话是xxx」来添加"

                if len(contacts) == 1:
                    c = contacts[0]
                    return f"📇 你记录了1个联系人：\n\n👤 {c.name}"

                reply = f"📇 你记录了{len(contacts)}个联系人：\n"
                for i, c in enumerate(contacts, 1):
                    reply += f"\n{i}. {c.name}"
                    if c.birthday:
                        reply += f" 🎂{c.birthday}"

                return reply

        except Exception as e:
            logger.error(f"查询联系人失败: {e}", exc_info=True)
            return "❌ 查询失败，请稍后重试"

    async def _handle_delete(
        self,
        action: ContactAction,
        user_id: str,
        contact_service: ContactService
    ) -> str:
        """删除联系人"""
        if not action.name:
            return "❓ 请告诉我要删除哪个联系人"

        try:
            # 先查找
            contact = await contact_service.find_by_name(user_id, action.name)
            if not contact:
                return f"🔍 没有找到「{action.name}」"

            # 删除
            success = await contact_service.delete_contact(contact.id, user_id)

            if success:
                return f"✅ 已删除联系人：{action.name}"
            else:
                return "❌ 删除失败"

        except Exception as e:
            logger.error(f"删除联系人失败: {e}", exc_info=True)
            return "❌ 删除失败，请稍后重试"


# 全局实例
contact_executor = ContactExecutor()
