"""
微信消息处理服务
"""
import xml.etree.ElementTree as ET
import logging
import time
from typing import Optional, Dict, Any

logger = logging.getLogger(__name__)


class WeChatService:
    """微信消息处理服务"""

    @staticmethod
    def parse_message(xml_data: str) -> Optional[Dict[str, Any]]:
        """
        解析微信XML消息

        Args:
            xml_data: 微信发送的XML格式消息

        Returns:
            解析后的消息字典
        """
        try:
            root = ET.fromstring(xml_data)
            message = {}

            # 解析所有子节点
            for child in root:
                message[child.tag] = child.text

            logger.debug(f"解析消息成功: {message}")
            return message

        except Exception as e:
            logger.error(f"解析XML消息失败: {e}", exc_info=True)
            return None

    @staticmethod
    def create_response_xml(
        content: str,
        from_user: str,
        to_user: str,
        msg_type: str = "text"
    ) -> str:
        """
        创建微信回复XML

        Args:
            content: 回复内容
            from_user: 发送方OpenID
            to_user: 接收方OpenID（公众号的原始ID）
            msg_type: 消息类型，默认为text

        Returns:
            XML格式的回复消息
        """
        create_time = int(time.time())

        xml_template = f"""<xml>
<ToUserName><![CDATA[{from_user}]]></ToUserName>
<FromUserName><![CDATA[{to_user}]]></FromUserName>
<CreateTime>{create_time}</CreateTime>
<MsgType><![CDATA[{msg_type}]]></MsgType>
<Content><![CDATA[{content}]]></Content>
</xml>"""

        return xml_template

    @staticmethod
    def create_empty_response() -> str:
        """
        创建空响应（用于表示已处理但无回复）
        """
        return "success"

    @staticmethod
    def validate_message(message: Dict[str, Any]) -> bool:
        """
        验证消息是否有效

        Args:
            message: 消息字典

        Returns:
            是否有效
        """
        required_fields = ["ToUserName", "FromUserName", "CreateTime", "MsgType"]
        return all(field in message for field in required_fields)

    @staticmethod
    def get_message_type(message: Dict[str, Any]) -> str:
        """
        获取消息类型

        Args:
            message: 消息字典

        Returns:
            消息类型
        """
        return message.get("MsgType", "")

    @staticmethod
    def is_text_message(message: Dict[str, Any]) -> bool:
        """
        判断是否为文本消息

        Args:
            message: 消息字典

        Returns:
            是否为文本消息
        """
        return message.get("MsgType") == "text"

    @staticmethod
    def get_user_id(message: Dict[str, Any]) -> str:
        """
        获取用户OpenID

        Args:
            message: 消息字典

        Returns:
            用户OpenID
        """
        return message.get("FromUserName", "")

    @staticmethod
    def get_content(message: Dict[str, Any]) -> str:
        """
        获取消息内容

        Args:
            message: 消息字典

        Returns:
            消息内容
        """
        return message.get("Content", "")
