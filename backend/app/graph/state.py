"""LangGraph 案件状态及与现有 CaseState 的转换。"""
from __future__ import annotations

from datetime import datetime
from typing import Any, TypedDict

from app.schemas.models import CaseState


class CaseGraphState(TypedDict, total=False):
    """图内状态使用可序列化 dict，便于 SQLite checkpoint 恢复。"""

    case_id: str
    created_at: str
    input: dict[str, Any]
    transcript: str
    transcript_source: str
    understanding: dict[str, Any] | None
    classification: dict[str, Any] | None
    work_order: dict[str, Any] | None
    reply: dict[str, Any] | None
    confirmed: bool
    audit_log: list[dict[str, Any]]
    retrieved_contexts: dict[str, list[dict[str, Any]]]
    rag_status: dict[str, Any]
    quality_flags: list[str]
    human_review_required: bool
    next_action: str | None
    graph_trace: list[dict[str, Any]]
    target_stage: str


def now() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def append_trace(
    state: CaseGraphState,
    node: str,
    **details: Any,
) -> list[dict[str, Any]]:
    trace = list(state.get("graph_trace") or [])
    trace.append({"node": node, "at": now(), **details})
    return trace


def append_audit(
    state: CaseGraphState,
    action: str,
    **details: Any,
) -> list[dict[str, Any]]:
    audit_log = list(state.get("audit_log") or [])
    audit_log.append({"action": action, "at": now(), **details})
    return audit_log


def case_to_graph_state(case: CaseState, target_stage: str) -> CaseGraphState:
    """将现有案件载入图状态，保留原有 API / SQLite 数据结构。"""
    data = case.model_dump(mode="json")
    understanding = data.get("understanding")
    return {
        **data,
        "transcript": (understanding or {}).get("transcript", ""),
        "transcript_source": (understanding or {}).get("transcript_source", ""),
        "retrieved_contexts": data.get("retrieved_contexts") or {},
        "rag_status": data.get("rag_status") or {},
        "quality_flags": data.get("quality_flags") or [],
        "human_review_required": bool(data.get("human_review_required")),
        "next_action": data.get("next_action"),
        "graph_trace": data.get("graph_trace") or [],
        "target_stage": target_stage,
    }


def graph_state_to_case(state: CaseGraphState) -> CaseState:
    """只取 CaseState 所需字段，忽略图内控制字段。"""
    return CaseState.model_validate(
        {
            "case_id": state["case_id"],
            "created_at": state["created_at"],
            "input": state.get("input") or {},
            "understanding": state.get("understanding"),
            "work_order": state.get("work_order"),
            "classification": state.get("classification"),
            "reply": state.get("reply"),
            "confirmed": bool(state.get("confirmed")),
            "audit_log": state.get("audit_log") or [],
            "retrieved_contexts": state.get("retrieved_contexts") or {},
            "rag_status": state.get("rag_status") or {},
            "quality_flags": state.get("quality_flags") or [],
            "human_review_required": bool(state.get("human_review_required")),
            "next_action": state.get("next_action"),
            "graph_trace": state.get("graph_trace") or [],
        }
    )
