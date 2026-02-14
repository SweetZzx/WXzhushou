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

                # 解析响应
                # 响应格式: {"choices": [{"message": {"content": "识别的文字"}}]}
                text = None
                for item in response:
                    if hasattr(item, 'choices') and item.choices:
                        text = item.choices[0].message.content
                        break
                    elif isinstance(item, dict) and 'choices' in item:
                        text = item['choices'][0]['message']['content']
                        break

                if text:
                    logger.info(f"语音识别成功: {text}")
                    return text
                else:
                    logger.warning("语音识别返回空结果")
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
