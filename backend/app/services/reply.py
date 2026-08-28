"""回复辅助编排：优先 LLM，失败时回退本地引擎。"""
from __future__ import annotations

from app.schemas.models import ClassificationResult, ReplyResult, UnderstandingResult
from app.services import llm, local_engine


def generate_reply(
    understanding: UnderstandingResult,
    classification: ClassificationResult | None = None,
) -> ReplyResult:
    category_name = classification.category_name if classification else None

    if llm.is_available():
        system = (
            "你是 12345 热线回复辅助助手。请基于理解与分类给出回复辅助，"
            "仅返回 JSON：acceptance_notice(受理提示), handling_suggestion(办理建议), "
            "pre_reply(预回复正文), callback_script(回访话术), "
            "modification_tips(修改建议数组)。"
        )
        user = (
            f"理解：{understanding.model_dump_json()}\n"
            f"分类：{(classification.model_dump_json() if classification else '无')}"
        )
        raw = llm.chat(system, user)
        data = llm.extract_json(raw) if raw else None
        if data and data.get("pre_reply"):
            return ReplyResult(
                acceptance_notice=data.get("acceptance_notice", ""),
                handling_suggestion=data.get("handling_suggestion", ""),
                pre_reply=data.get("pre_reply", ""),
                callback_script=data.get("callback_script", ""),
                modification_tips=data.get("modification_tips") or [],
                source="llm",
            )

    return local_engine.reply(understanding, category_name, classification)
