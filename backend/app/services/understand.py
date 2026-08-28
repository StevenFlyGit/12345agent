"""诉求理解编排：优先 LLM，失败时回退本地引擎。"""
from __future__ import annotations

import json

from app.schemas.models import UnderstandingResult
from app.services import llm, local_engine


def understand(text: str, transcript_source: str = "text") -> UnderstandingResult:
    """对文本做诉求理解，返回结构化要素。source 标注 ll m / local-engine。"""
    if llm.is_available():
        system = (
            "你是 12345 政务服务热线诉求理解助手。请从群众诉求文本中抽取要素，"
            "仅返回 JSON，字段如下："
            "time(时间,字符串或null), location(地点,字符串或null), "
            "parties(涉及人员数组), event(主要事件,字符串或null), "
            "demand(群众诉求,字符串或null), other(其他,字符串或null), "
            "needs_clarification(布尔), missing_fields(缺失字段中文数组), "
            "urgent(布尔), repeat_request(布尔)。"
        )
        user = f"文本：{text}"
        raw = llm.chat(system, user)
        data = llm.extract_json(raw) if raw else None
        if data:
            try:
                return UnderstandingResult(
                    transcript=text,
                    transcript_source=transcript_source,
                    time=data.get("time"),
                    location=data.get("location"),
                    parties=data.get("parties") or [],
                    event=data.get("event"),
                    demand=data.get("demand"),
                    other=data.get("other"),
                    needs_clarification=bool(data.get("needs_clarification", False)),
                    missing_fields=data.get("missing_fields") or [],
                    urgent=bool(data.get("urgent", False)),
                    repeat_request=bool(data.get("repeat_request", False)),
                    source="llm",
                )
            except Exception:
                pass

    # 本地回退
    result = local_engine.understand(text)
    result.transcript_source = transcript_source
    return result
