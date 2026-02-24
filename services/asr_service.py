"""
语音识别服务
使用智谱GLM-ASR进行语音转文字
"""
import logging
import tempfile
import os
from typing import Optional
from io import BytesIO

from zhipuai import ZhipuAI

from config import ZHIPU_API_KEY

logger = logging.getLogger(__name__)


class ASRService:
    """语音识别服务"""

    def __init__(self, api_key: str = None):
        self.client = ZhipuAI(api_key=api_key or ZHIPU_API_KEY)

    async def transcribe(self, audio_data: bytes) -> Optional[str]:
        """
        将音频数据转换为文字

        Args:
            audio_data: 音频文件的二进制数据（支持WAV、MP3等格式）

        Returns:
            识别出的文字内容，失败返回None
        """
        try:
            # 使用临时文件处理音频数据
            with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as temp_file:
                temp_file.write(audio_data)
                temp_path = temp_file.name

            try:
                # 调用智谱ASR API
                with open(temp_path, "rb") as audio_file:
                    response = self.client.audio.transcriptions.create(
                        model="glm-asr",
                        file=audio_file,
                        stream=False
                    )

                logger.debug(f"ASR响应类型: {type(response)}, 内容: {response}")

                # 解析响应 - 智谱ASR响应格式
                text = None

                # 方式1: 直接访问text属性（智谱ASR格式）
                if hasattr(response, 'text') and response.text:
                    text = response.text
                # 方式2: 从segments中获取
                elif hasattr(response, 'segments') and response.segments:
                    text = ''.join(seg.get('text', '') for seg in response.segments)
                # 方式3: 作为字典访问
                elif isinstance(response, dict):
                    if 'text' in response:
                        text = response['text']
                    elif 'segments' in response:
                        text = ''.join(seg.get('text', '') for seg in response['segments'])

                if text:
                    logger.info(f"语音识别成功: {text}")
                    return text
                else:
                    logger.warning(f"语音识别返回空结果, response: {response}")
                    return None

            finally:
                # 清理临时文件
                if os.path.exists(temp_path):
                    os.unlink(temp_path)

        except Exception as e:
            logger.error(f"语音识别失败: {e}", exc_info=True)
            return None

    async def transcribe_from_url(self, audio_url: str) -> Optional[str]:
        """
        从URL下载音频并转换为文字

        Args:
            audio_url: 音频文件的URL

        Returns:
            识别出的文字内容，失败返回None
        """
        try:
            import httpx

            async with httpx.AsyncClient(timeout=30) as client:
                response = await client.get(audio_url)
                if response.status_code == 200:
                    return await self.transcribe(response.content)
                else:
                    logger.error(f"下载音频失败: HTTP {response.status_code}")
                    return None

        except Exception as e:
            logger.error(f"从URL下载音频失败: {e}", exc_info=True)
            return None
