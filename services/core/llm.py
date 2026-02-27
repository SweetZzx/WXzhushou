"""
LLM 封装模块
使用 ChatOpenAI 兼容接口，便于切换模型
"""
import os
import logging
from typing import Optional

from langchain_openai import ChatOpenAI

from config import ZHIPU_API_KEY, ZHIPU_API_BASE, ZHIPU_MODEL

logger = logging.getLogger(__name__)


def get_llm(
    model: Optional[str] = None,
    temperature: float = 0.7,
    max_tokens: int = 2000,
    **kwargs
) -> ChatOpenAI:
    """
    获取 LLM 实例

    Args:
        model: 模型名称，默认使用配置中的 ZHIPU_MODEL
        temperature: 温度参数，0-1
        max_tokens: 最大 token 数
        **kwargs: 其他 ChatOpenAI 参数

    Returns:
        ChatOpenAI 实例
    """
    model_name = model or ZHIPU_MODEL
    llm = ChatOpenAI(
        model=model_name,
        openai_api_key=ZHIPU_API_KEY,
        openai_api_base=ZHIPU_API_BASE,
        temperature=temperature,
        max_tokens=max_tokens,
        **kwargs
    )
    logger.info(f"LLM 实例创建成功: model={model_name}")
    return llm


# 预配置的 LLM 实例（延迟初始化）
_llm_instance: Optional[ChatOpenAI] = None


def get_default_llm() -> ChatOpenAI:
    """获取默认的 LLM 实例（单例）"""
    global _llm_instance
    if _llm_instance is None:
        _llm_instance = get_llm()
    return _llm_instance
