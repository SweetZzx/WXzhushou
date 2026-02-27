"""
微信主动推送服务
使用客服消息接口主动向用户发送消息
"""
import httpx
import logging
from typing import Optional
from datetime import datetime, timedelta

from config import WECHAT_APP_ID, WECHAT_APP_SECRET

logger = logging.getLogger(__name__)


class WeChatPushService:
    """微信主动推送服务"""

    def __init__(self):
        self.app_id = WECHAT_APP_ID
        self.app_secret = WECHAT_APP_SECRET
        self._access_token: Optional[str] = None
        self._token_expires_at: Optional[datetime] = None

    async def get_access_token(self) -> Optional[str]:
        """获取微信 access_token"""
        # 检查缓存
        if self._access_token and self._token_expires_at:
            if datetime.now() < self._token_expires_at:
                return self._access_token

        # 请求新 token
        url = f"https://api.weixin.qq.com/cgi-bin/token?grant_type=client_credential&appid={self.app_id}&secret={self.app_secret}"

        try:
            async with httpx.AsyncClient(timeout=10) as client:
                response = await client.get(url)
                data = response.json()

                if "access_token" in data:
                    self._access_token = data["access_token"]
                    expires_in = data.get("expires_in", 7200)
                    self._token_expires_at = datetime.now() + timedelta(seconds=expires_in - 300)
                    logger.info("获取微信 access_token 成功")
                    return self._access_token
                else:
                    logger.error(f"获取 access_token 失败: {data}")
                    return None

        except Exception as e:
            logger.error(f"请求 access_token 失败: {e}", exc_info=True)
            return None

    async def send_text_message(self, user_id: str, content: str) -> bool:
        """
        发送文本消息给用户

        Args:
            user_id: 用户的 OpenID
            content: 消息内容

        Returns:
            是否发送成功
        """
        logger.info(f"准备发送消息: user_id={user_id}")

        access_token = await self.get_access_token()
        if not access_token:
            logger.error("无法获取 access_token")
            return False

        url = f"https://api.weixin.qq.com/cgi-bin/message/custom/send?access_token={access_token}"

        payload = {
            "touser": user_id,
            "msgtype": "text",
            "text": {"content": content}
        }

        try:
            async with httpx.AsyncClient(timeout=10) as client:
                response = await client.post(url, json=payload)
                data = response.json()

                if data.get("errcode") == 0:
                    logger.info(f"消息发送成功: user_id={user_id}")
                    return True
                else:
                    logger.error(f"消息发送失败: {data}")
                    return False

        except Exception as e:
            logger.error(f"发送消息异常: {e}", exc_info=True)
            return False

    async def send_template_message(
        self,
        user_id: str,
        template_id: str,
        data: dict,
        url: Optional[str] = None
    ) -> bool:
        """发送模板消息"""
        access_token = await self.get_access_token()
        if not access_token:
            return False

        api_url = f"https://api.weixin.qq.com/cgi-bin/message/template/send?access_token={access_token}"

        payload = {
            "touser": user_id,
            "template_id": template_id,
            "data": data
        }

        if url:
            payload["url"] = url

        try:
            async with httpx.AsyncClient(timeout=10) as client:
                response = await client.post(api_url, json=payload)
                result = response.json()

                if result.get("errcode") == 0:
                    logger.info(f"模板消息发送成功: user_id={user_id}")
                    return True
                else:
                    logger.error(f"模板消息发送失败: {result}")
                    return False

        except Exception as e:
            logger.error(f"发送模板消息异常: {e}", exc_info=True)
            return False


# 全局实例
wechat_push_service = WeChatPushService()
