"""LangChain ChatModel 初始化。

集中封装 OpenAI 兼容模型，业务代码只依赖 LangChain Runnable。
"""
from __future__ import annotations

from functools import lru_cache

from langchain_openai import ChatOpenAI

from app.config import LLM_AVAILABLE, settings


def is_available() -> bool:
    """是否启用真实 LLM。"""
    return LLM_AVAILABLE


@lru_cache(maxsize=1)
def get_chat_model() -> ChatOpenAI | None:
    """返回 LangChain ChatModel；无 Key 时返回 None。"""
    if not is_available():
        return None

    kwargs = {
        "api_key": settings.LLM_API_KEY,
        "model": settings.LLM_MODEL,
        "temperature": 0.2,
        "timeout": 20,
    }
    if settings.LLM_BASE_URL:
        kwargs["base_url"] = settings.LLM_BASE_URL
    return ChatOpenAI(**kwargs)

