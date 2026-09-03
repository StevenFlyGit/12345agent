"""工单生成编排：优先 LLM，失败时回退本地引擎。"""
from __future__ import annotations

from app.chains.models import is_available as llm_available
from app.chains.workorder_chain import invoke_workorder_chain
from app.rag.retrievers import format_hits_for_prompt, retrieve_for_workorder
from app.schemas.models import ClassificationResult, UnderstandingResult, WorkOrder
from app.services import local_engine


def generate_work_order(
    text: str,
    understanding: UnderstandingResult,
    classification: ClassificationResult | None = None,
    *,
    context: str | None = None,
) -> WorkOrder:
    category_name = classification.category_name if classification else None

    prompt_context = context
    if prompt_context is None:
        prompt_context = "无"
        if llm_available():
            prompt_context = format_hits_for_prompt(retrieve_for_workorder(text))
    payload = invoke_workorder_chain(text, understanding, classification, context=prompt_context)
    if payload is not None and payload.title:
        return WorkOrder(
            title=payload.title,
            summary=payload.summary,
            content=payload.content or text,
            key_elements=payload.key_elements,
            suggested_category=payload.suggested_category or category_name,
            source="llm",
        )

    return local_engine.work_order(text, understanding, category_name)
