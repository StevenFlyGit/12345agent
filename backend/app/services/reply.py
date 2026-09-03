"""回复辅助编排：优先 LLM，失败时回退本地引擎。"""
from __future__ import annotations

from app.chains.models import is_available as llm_available
from app.chains.reply_chain import invoke_reply_chain
from app.rag.retrievers import format_hits_for_prompt, retrieve_for_reply
from app.schemas.models import ClassificationResult, ReplyResult, UnderstandingResult
from app.services import local_engine


def generate_reply(
    understanding: UnderstandingResult,
    classification: ClassificationResult | None = None,
) -> ReplyResult:
    category_name = classification.category_name if classification else None

    context = "无"
    if llm_available():
        query = "\n".join(
            part
            for part in [
                understanding.transcript,
                understanding.event or "",
                understanding.demand or "",
            ]
            if part
        )
        context = format_hits_for_prompt(
            retrieve_for_reply(query, category_name=category_name)
        )
    payload = invoke_reply_chain(understanding, classification, context=context)
    if payload is not None and payload.pre_reply:
        return ReplyResult(
            acceptance_notice=payload.acceptance_notice,
            handling_suggestion=payload.handling_suggestion,
            pre_reply=payload.pre_reply,
            callback_script=payload.callback_script,
            modification_tips=payload.modification_tips,
            source="llm",
        )

    return local_engine.reply(understanding, category_name, classification)
