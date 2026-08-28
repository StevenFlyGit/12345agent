"""工单生成编排：优先 LLM，失败时回退本地引擎。"""
from __future__ import annotations

from app.schemas.models import ClassificationResult, UnderstandingResult, WorkOrder
from app.services import llm, local_engine


def generate_work_order(
    text: str,
    understanding: UnderstandingResult,
    classification: ClassificationResult | None = None,
) -> WorkOrder:
    category_name = classification.category_name if classification else None

    if llm.is_available():
        system = (
            "你是 12345 热线工单生成助手。请基于已理解的诉求生成工单，"
            "仅返回 JSON：title(标题), summary(摘要), content(正文，可含原文), "
            "key_elements(关键要素数组), suggested_category(建议类别中文名或null)。"
        )
        user = f"原文：{text}\n已理解：{understanding.model_dump_json()}"
        raw = llm.chat(system, user)
        data = llm.extract_json(raw) if raw else None
        if data and data.get("title"):
            return WorkOrder(
                title=data["title"],
                summary=data.get("summary", ""),
                content=data.get("content", text),
                key_elements=data.get("key_elements") or [],
                suggested_category=data.get("suggested_category") or category_name,
                source="llm",
            )

    return local_engine.work_order(text, understanding, category_name)
