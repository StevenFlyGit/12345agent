"""分类与承办单位推荐编排：优先 LLM，失败时回退本地引擎。"""
from __future__ import annotations

from app.data import loaders
from app.schemas.models import ClassificationResult, DepartmentSuggestion, UnderstandingResult
from app.services import llm, local_engine

_NAME_TO_CODE = loaders.category_name_to_code()


def classify(text: str, understanding: UnderstandingResult | None = None) -> ClassificationResult:
    """对文本分类并推荐承办单位。始终依据 department_rules.json 生成建议。"""
    category_code: str | None = None
    category_name: str | None = None
    confidence: float = 0.0
    needs_manual: bool = False
    source = "local-engine"

    if llm.is_available():
        system = (
            "你是 12345 热线工单分类助手。请判断群众诉求所属类别，"
            "仅返回 JSON：category_name(12类之一的中文名)，confidence(0-1浮点)，"
            "needs_manual(布尔，信息不足或跨类别时为真)。"
            "12 类为：经济财贸、卫生健康、市场监管、生态环境、公共服务、城乡建设、"
            "公共安全、劳动和社会保障、交通运输、科教文体、农林水土、城市管理。"
        )
        user = f"文本：{text}"
        raw = llm.chat(system, user)
        data = llm.extract_json(raw) if raw else None
        if data and data.get("category_name"):
            category_name = data["category_name"]
            category_code = _NAME_TO_CODE.get(category_name)
            confidence = float(data.get("confidence", 0.0) or 0.0)
            needs_manual = bool(data.get("needs_manual", False))
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
