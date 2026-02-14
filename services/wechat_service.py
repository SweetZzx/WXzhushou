"""
微信消息处理服务
"""
import xml.etree.ElementTree as ET
import logging
import time
from typing import Optional, Dict, Any
import httpx

from config import WECHAT_APP_ID, WECHAT_APP_SECRET

logger = logging.getLogger(__name__)


class WeChatMediaService:
    """微信媒体文件服务"""

    def __init__(self):
        self._access_token: Optional[str] = None
        self._token_expires_at: int = 0

    async def get_access_token(self) -> Optional[str]:
        """获取微信access_token"""
        # 检查缓存是否有效
        if self._access_token and time.time() < self._token_expires_at:
            return self._access_token

        try:
            url = f"https://api.weixin.qq.com/cgi-bin/token?grant_type=client_credential&appid={WECHAT_APP_ID}&secret={WECHAT_APP_SECRET}"

            async with httpx.AsyncClient(timeout=10) as client:
                response = await client.get(url)
                data = response.json()

                if "access_token" in data:
                    self._access_token = data["access_token"]
                    # 提前5分钟过期
                    self._token_expires_at = time.time() + data.get("expires_in", 7200) - 300
                    logger.info("获取微信access_token成功")
                    return self._access_token
                else:
                    logger.error(f"获取access_token失败: {data}")
                    return None

        except Exception as e:
            logger.error(f"获取access_token异常: {e}", exc_info=True)
            return None

    async def download_media(self, media_id: str) -> Optional[bytes]:
        """
        下载微信媒体文件

        Args:
            media_id: 媒体文件ID

        Returns:
            媒体文件的二进制数据，失败返回None
        """
        try:
            access_token = await self.get_access_token()
            if not access_token:
                logger.error("无法获取access_token，下载媒体文件失败")
                return None

            url = f"https://api.weixin.qq.com/cgi-bin/media/get?access_token={access_token}&media_id={media_id}"

            async with httpx.AsyncClient(timeout=30) as client:
                response = await client.get(url)

                if response.status_code == 200:
                    # 检查是否是错误响应（JSON格式）
                    content_type = response.headers.get("content-type", "")
                    if "application/json" in content_type:
                        error_data = response.json()
                        logger.error(f"下载媒体文件失败: {error_data}")
                        return None

                    logger.info(f"下载媒体文件成功: media_id={media_id}, size={len(response.content)}")
                    return response.content
                else:
                    logger.error(f"下载媒体文件失败: HTTP {response.status_code}")
                    return None

        except Exception as e:
            logger.error(f"下载媒体文件异常: {e}", exc_info=True)
            return None


# 全局媒体服务实例
media_service = WeChatMediaService()


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
