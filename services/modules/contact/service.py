"""
联系人服务
提供联系人的 CRUD 操作，包含加密功能
"""
import logging
from typing import Optional, List
from datetime import datetime
from sqlalchemy import select, or_
from sqlalchemy.exc import IntegrityError

from models.contact import Contact
from utils.crypto import aes_encrypt, aes_decrypt
from config import CONTACT_ENCRYPT_KEY

logger = logging.getLogger(__name__)


def get_encrypt_key() -> bytes:
    """获取加密密钥（32字节）"""
    key = CONTACT_ENCRYPT_KEY.encode("utf-8")
    # 确保密钥是32字节
    if len(key) < 32:
        key = key + b'0' * (32 - len(key))
    return key[:32]


class ContactService:
    """联系人服务"""

    def __init__(self, db_session):
        self.db = db_session
        self.encrypt_key = get_encrypt_key()

    def _encrypt(self, plaintext: str) -> str:
        """加密敏感数据"""
        if not plaintext:
            return ""
        return aes_encrypt(plaintext, self.encrypt_key)

    def _decrypt(self, ciphertext: str) -> str:
        """解密敏感数据"""
        if not ciphertext:
            return ""
        try:
            return aes_decrypt(ciphertext, self.encrypt_key)
        except Exception as e:
            logger.error(f"解密失败: {e}")
            return ciphertext  # 返回原文（可能是未加密的旧数据）

    async def create_contact(
        self,
        user_id: str,
        name: str,
        phone: Optional[str] = None,
        birthday: Optional[str] = None,
        remark: Optional[str] = None,
        extra: Optional[str] = None
    ) -> Contact:
        """创建联系人"""
        try:
            contact = Contact(
                user_id=user_id,
                name=name,
                phone=self._encrypt(phone) if phone else None,
                birthday=birthday,
                remark=remark,
                extra=extra
            )
            self.db.add(contact)
            await self.db.commit()
            await self.db.refresh(contact)
            logger.info(f"创建联系人成功: user={user_id}, name={name}")
            return contact
        except IntegrityError as e:
            await self.db.rollback()
            logger.error(f"创建联系人失败: {e}")
            raise

    async def find_by_name(self, user_id: str, name: str) -> Optional[Contact]:
        """根据姓名查找联系人"""
        result = await self.db.execute(
            select(Contact).where(
                Contact.user_id == user_id,
                Contact.name == name
            )
        )
        return result.scalar_one_or_none()

    async def search_contacts(self, user_id: str, keyword: str) -> List[Contact]:
        """搜索联系人（按姓名或备注）"""
        result = await self.db.execute(
            select(Contact).where(
                Contact.user_id == user_id,
                or_(
                    Contact.name.contains(keyword),
                    Contact.remark.contains(keyword)
                )
            )
        )
        return result.scalars().all()

    async def list_contacts(self, user_id: str) -> List[Contact]:
        """列出用户所有联系人"""
        result = await self.db.execute(
            select(Contact)
            .where(Contact.user_id == user_id)
            .order_by(Contact.name)
        )
        return result.scalars().all()

    async def update_contact(
        self,
        contact_id: int,
        user_id: str,
        name: Optional[str] = None,
        phone: Optional[str] = None,
        birthday: Optional[str] = None,
        remark: Optional[str] = None,
        extra: Optional[str] = None
    ) -> Optional[Contact]:
        """更新联系人信息"""
        try:
            result = await self.db.execute(
                select(Contact).where(
                    Contact.id == contact_id,
                    Contact.user_id == user_id
                )
            )
            contact = result.scalar_one_or_none()

            if not contact:
                return None

            if name is not None:
                contact.name = name
            if phone is not None:
                contact.phone = self._encrypt(phone)
            if birthday is not None:
                contact.birthday = birthday
            if remark is not None:
                contact.remark = remark
            if extra is not None:
                contact.extra = extra

            contact.updated_at = datetime.now().isoformat()
            await self.db.commit()
            await self.db.refresh(contact)

            logger.info(f"更新联系人成功: id={contact_id}")
            return contact

        except Exception as e:
            await self.db.rollback()
            logger.error(f"更新联系人失败: {e}")
            raise

    async def upsert_contact(
        self,
        user_id: str,
        name: str,
        phone: Optional[str] = None,
        birthday: Optional[str] = None,
        remark: Optional[str] = None,
        extra: Optional[str] = None
    ) -> tuple[Contact, bool]:
        """创建或更新联系人（智能合并）"""
        existing = await self.find_by_name(user_id, name)

        if existing:
            # 更新现有联系人，只更新非空字段
            update_data = {}
            if phone and not existing.phone:
                update_data['phone'] = phone
            if birthday and not existing.birthday:
                update_data['birthday'] = birthday
            if remark and not existing.remark:
                update_data['remark'] = remark
            if extra:
                update_data['extra'] = extra

            if update_data:
                for key, value in update_data.items():
                    if key == 'phone':
                        setattr(existing, key, self._encrypt(value))
                    else:
                        setattr(existing, key, value)
                existing.updated_at = datetime.now().isoformat()
                await self.db.commit()
                await self.db.refresh(existing)

            return existing, False
        else:
            # 创建新联系人
            contact = await self.create_contact(
                user_id=user_id,
                name=name,
                phone=phone,
                birthday=birthday,
                remark=remark,
                extra=extra
            )
            return contact, True

    async def delete_contact(self, contact_id: int, user_id: str) -> bool:
        """删除联系人"""
        try:
            result = await self.db.execute(
                select(Contact).where(
                    Contact.id == contact_id,
                    Contact.user_id == user_id
                )
            )
            contact = result.scalar_one_or_none()

            if not contact:
                return False

            await self.db.delete(contact)
            await self.db.commit()

            logger.info(f"删除联系人成功: id={contact_id}")
            return True

        except Exception as e:
            await self.db.rollback()
            logger.error(f"删除联系人失败: {e}")
            return False

    async def get_birthday_contacts(self, month: int, day: int) -> List[dict]:
        """获取指定日期过生日的联系人（用于提醒）"""
        birthday_str = f"{month:02d}-{day:02d}"

        result = await self.db.execute(
            select(Contact).where(Contact.birthday == birthday_str)
        )
        contacts = result.scalars().all()

        return [
            {
                "user_id": c.user_id,
                "name": c.name,
                "phone": self._decrypt(c.phone) if c.phone else None,
                "remark": c.remark
            }
            for c in contacts
        ]

    async def get_upcoming_birthdays(self, days: int = 7) -> List[dict]:
        """获取未来N天内过生日的联系人"""
        from datetime import date, timedelta

        today = date.today()
        contacts = []

        for i in range(days + 1):
            check_date = today + timedelta(days=i)
            birthday_str = f"{check_date.month:02d}-{check_date.day:02d}"

            result = await self.db.execute(
                select(Contact).where(Contact.birthday == birthday_str)
            )
            day_contacts = result.scalars().all()

            for c in day_contacts:
                contacts.append({
                    "days_until": i,
                    "user_id": c.user_id,
                    "name": c.name,
                    "phone": self._decrypt(c.phone) if c.phone else None,
                    "remark": c.remark,
                    "birthday": c.birthday
                })

        return contacts

    def get_decrypted_phone(self, contact: Contact) -> str:
        """获取解密后的电话号码"""
        return self._decrypt(contact.phone) if contact.phone else ""
