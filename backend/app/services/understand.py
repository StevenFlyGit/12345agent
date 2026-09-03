"""诉求理解编排：优先 LLM，失败时回退本地引擎。"""
from __future__ import annotations

from app.chains.understand_chain import invoke_understand_chain
from app.schemas.models import UnderstandingResult
from app.services import local_engine


def understand(text: str, transcript_source: str = "text") -> UnderstandingResult:
    """对文本做诉求理解，返回结构化要素。source 标注 llm / local-engine。"""
    payload = invoke_understand_chain(text)
    if payload is not None:
        return UnderstandingResult(
            transcript=text,
            transcript_source=transcript_source,
            time=payload.time,
            location=payload.location,
            parties=payload.parties,
            event=payload.event,
            demand=payload.demand,
            other=payload.other,
            needs_clarification=payload.needs_clarification,
            missing_fields=payload.missing_fields,
            urgent=payload.urgent,
            repeat_request=payload.repeat_request,
            source="llm",
        )

    # 本地回退
    result = local_engine.understand(text)
    result.transcript_source = transcript_source
    return result
