"""分类与承办单位推荐编排：优先 LLM，失败时回退本地引擎。"""
from __future__ import annotations

from app.chains.classify_chain import invoke_classify_chain
from app.chains.models import is_available as llm_available
from app.data import loaders
from app.rag.retrievers import format_hits_for_prompt, retrieve_for_classification
from app.schemas.models import ClassificationResult, DepartmentSuggestion, UnderstandingResult
from app.services import local_engine

_NAME_TO_CODE = loaders.category_name_to_code()


def classify(
    text: str,
    understanding: UnderstandingResult | None = None,
    *,
    context: str | None = None,
) -> ClassificationResult:
    """对文本分类并推荐承办单位。始终依据 department_rules.json 生成建议。"""
    category_code: str | None = None
    category_name: str | None = None
    confidence: float = 0.0
    needs_manual: bool = False
    source = "local-engine"

    prompt_context = context
    if prompt_context is None:
        prompt_context = "无"
        if llm_available():
            prompt_context = format_hits_for_prompt(retrieve_for_classification(text))
    payload = invoke_classify_chain(text, understanding, context=prompt_context)
    if payload is not None and payload.category_name:
        category_name = payload.category_name
        category_code = _NAME_TO_CODE.get(category_name)
        if category_code is not None:
            confidence = float(payload.confidence or 0.0)
            needs_manual = bool(payload.needs_manual)
            source = "llm"

    if category_code is None:
        # 本地回退
        full = local_engine.classify_full(text)
        category_code = full["category_code"]
        category_name = full["category_name"]
        confidence = full["confidence"]
        needs_manual = full["needs_manual"]
        source = "local-engine"

    suggestions = local_engine.build_department_suggestions(text, category_code, category_name)

    manual_hint = None
    if needs_manual or confidence < 0.3:
        tail = "职责交叉/信息不足，建议人工复核。"
        manual_hint = tail
        if suggestions:
            suggestions[-1].reason = suggestions[-1].reason + "。" + tail
        elif category_code is None:
            suggestions = [
                DepartmentSuggestion(main="待人工研判", co=[], reason=tail)
            ]

    return ClassificationResult(
        category=category_code,
        category_name=category_name,
        confidence=confidence,
        suggestions=suggestions,
        needs_manual=needs_manual,
        manual_hint=manual_hint,
        source=source,
    )
