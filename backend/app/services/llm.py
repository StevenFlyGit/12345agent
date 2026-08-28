"""OpenAI 兼容的大模型客户端封装。

- 通过 app.config 的 LLM_AVAILABLE 判断可用性；
- chat() 超时 20s；任何异常或不可用均返回 None，由调用方回退本地引擎。
"""
from __future__ import annotations

from typing import Optional

from app.config import LLM_AVAILABLE, settings

_client = None


def is_available() -> bool:
    return LLM_AVAILABLE


def _get_client():
    global _client
    if _client is None:
        from openai import OpenAI

        _client = OpenAI(api_key=settings.LLM_API_KEY, base_url=settings.LLM_BASE_URL)
    return _client


def chat(system: str, user: str, timeout: int = 20) -> Optional[str]:
    """调用大模型聊天接口，返回文本内容；不可用或失败返回 None。"""
    if not LLM_AVAILABLE:
        return None
    try:
        resp = _get_client().chat.completions.create(
            model=settings.LLM_MODEL,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            temperature=0.2,
            timeout=timeout,
        )
        content = resp.choices[0].message.content
        return content.strip() if content else None
    except Exception:
        # 调用失败静默回退
        return None


def extract_json(text: str) -> Optional[dict]:
    """从模型返回中尽力解析 JSON（兼容 ```json 代码块）。"""
    if not text:
        return None
    t = text.strip()
    if t.startswith("```"):
        # 去掉 ```json ... ```
        t = t.split("```", 2)[1]
        if t.lower().startswith("json"):
            t = t[4:]
        t = t.strip()
    try:
        return __import__("json").loads(t)
    except Exception:
        return None
