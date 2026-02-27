"""
微信媒体文件服务
处理语音、图片等媒体文件的下载
"""
import httpx
import logging
from typing import Optional
from datetime import datetime, timedelta

from config import WECHAT_APP_ID, WECHAT_APP_SECRET

logger = logging.getLogger(__name__)


class WeChatMediaService:
    """微信媒体文件服务"""

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

    async def download_media(self, media_id: str) -> Optional[bytes]:
        """
        下载微信媒体文件

        Args:
            media_id: 媒体文件ID

        Returns:
            媒体文件的二进制数据，失败返回None
        """
        logger.info(f"下载媒体文件: media_id={media_id}")

        access_token = await self.get_access_token()
        if not access_token:
            logger.error("无法获取 access_token")
            return None

        url = f"https://api.weixin.qq.com/cgi-bin/media/get?access_token={access_token}&media_id={media_id}"

        try:
            async with httpx.AsyncClient(timeout=30) as client:
                response = await client.get(url)

                if response.status_code == 200:
                    content_type = response.headers.get("content-type", "")

                    # 检查是否返回了错误信息（JSON格式）
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


# 全局实例
wechat_media_service = WeChatMediaService()
