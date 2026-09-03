"""LangGraph 条件边。"""
from __future__ import annotations

from app.graph.state import CaseGraphState


def route_after_understand(state: CaseGraphState) -> str:
    return "persist" if state.get("target_stage") == "understand" else "retrieve_context"


def route_after_retrieve(state: CaseGraphState) -> str:
    return "reply" if state.get("target_stage") == "reply" else "classify"


def route_after_classify(state: CaseGraphState) -> str:
    target = state.get("target_stage")
    if target == "classify":
        return "persist"
    return "workorder"


def route_after_workorder(state: CaseGraphState) -> str:
    return "quality_check" if state.get("target_stage") == "full" else "persist"


def route_after_quality_check(state: CaseGraphState) -> str:
    return "human_review" if state.get("human_review_required") else "retrieve_reply_context"


def route_after_reply(state: CaseGraphState) -> str:
    return "human_review" if state.get("target_stage") == "full" else "persist"

