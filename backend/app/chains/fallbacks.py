"""LangChain 调用失败时的兜底工具。"""
from __future__ import annotations

from collections.abc import Callable
from typing import TypeVar

T = TypeVar("T")


def try_invoke(call: Callable[[], T]) -> T | None:
    """执行 chain，失败或模型不可用时返回 None。"""
    try:
        return call()
    except Exception:
        return None

