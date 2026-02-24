"""
LLM 封装模块
使用 ChatOpenAI 兼容接口，便于切换模型
"""
import os
import logging
from typing import Optional

from langchain_openai import ChatOpenAI

from config import ZHIPU_API_KEY

logger = logging.getLogger(__name__)

# 智谱 GLM API 配置
ZHIPU_API_BASE = "https://open.bigmodel.cn/api/paas/v4"
DEFAULT_MODEL = "glm-4"


def get_llm(
    model: Optional[str] = None,
    temperature: float = 0.7,
    max_tokens: int = 2000,
    **kwargs
) -> ChatOpenAI:
    """
    获取 LLM 实例

    Args:
        model: 模型名称，默认 glm-4
        temperature: 温度参数，0-1
        max_tokens: 最大 token 数
        **kwargs: 其他 ChatOpenAI 参数

    Returns:
        ChatOpenAI 实例
    """
    llm = ChatOpenAI(
        model=model or DEFAULT_MODEL,
        openai_api_key=ZHIPU_API_KEY,
        openai_api_base=ZHIPU_API_BASE,
        temperature=temperature,
        max_tokens=max_tokens,
        **kwargs
    )
    logger.info(f"LLM 实例创建成功: model={model or DEFAULT_MODEL}")
    return llm


# 预配置的 LLM 实例（延迟初始化）
_llm_instance: Optional[ChatOpenAI] = None


def get_default_llm() -> ChatOpenAI:
    """获取默认的 LLM 实例（单例）"""
    global _llm_instance
    if _llm_instance is None:
        _llm_instance = get_llm()
    return _llm_instance
