"""LangGraph 业务节点：复用既有服务函数，不重复实现业务规则。"""
from __future__ import annotations

from app.graph.state import CaseGraphState, append_audit, append_trace, graph_state_to_case
from app.rag.schemas import EvidenceItem
from app.rag.retrievers import (
    format_hits_for_prompt,
    retrieve_for_classification,
    retrieve_for_reply,
    retrieve_for_workorder,
)
from app.services import asr, classify as classify_svc, reply as reply_svc
from app.services import understand as understand_svc
from app.services import workorder as workorder_svc
from app.schemas.models import ClassificationResult, UnderstandingResult
from app.workflow import store


def _understanding(state: CaseGraphState) -> UnderstandingResult:
    payload = state.get("understanding")
    if not payload:
        raise ValueError("请先完成诉求理解")
    return UnderstandingResult.model_validate(payload)


def _classification(state: CaseGraphState) -> ClassificationResult | None:
    payload = state.get("classification")
    return ClassificationResult.model_validate(payload) if payload else None


def _format_context(state: CaseGraphState, key: str) -> str:
    """将 checkpoint 中的证据字典还原为 EvidenceItem 后再构造 Prompt 上下文。"""
    raw_hits = (state.get("retrieved_contexts") or {}).get(key, [])
    hits = [EvidenceItem.model_validate(hit) for hit in raw_hits]
    return format_hits_for_prompt(hits)


def prepare_input_node(state: CaseGraphState) -> dict:
    transcript = str(state.get("transcript") or "").strip()
    transcript_source = str(state.get("transcript_source") or "")
    if not transcript:
        input_data = state.get("input") or {}
        text = str(input_data.get("text") or "").strip()
        if text:
            transcript, transcript_source = text, "text"
        else:
            transcript, transcript_source = asr.transcribe(
                input_data.get("audio_filename"), None
            )
    return {
        "transcript": transcript,
        "transcript_source": transcript_source or "text",
        "graph_trace": append_trace(state, "prepare_input"),
    }


def understand_node(state: CaseGraphState) -> dict:
    understanding = understand_svc.understand(
        str(state.get("transcript") or ""),
        str(state.get("transcript_source") or "text"),
    )
    return {
        "understanding": understanding.model_dump(mode="json"),
        "next_action": "understand",
        "audit_log": append_audit(state, "understand"),
        "graph_trace": append_trace(state, "understand"),
    }


def retrieve_context_node(state: CaseGraphState) -> dict:
    """一次召回按用途分组保存，后续节点只消费 State 中的 Evidence。"""
    query = str(state.get("transcript") or "").strip()
    target = str(state.get("target_stage") or "")
    classification = _classification(state)
    contexts = dict(state.get("retrieved_contexts") or {})
    rag_status = dict(state.get("rag_status") or {})

    if target in {"classify", "workorder", "full"}:
        hits = retrieve_for_classification(query)
        contexts["classification"] = [hit.model_dump(mode="json") for hit in hits]
        rag_status["classification"] = {"count": len(hits), "status": "ok"}
    if target in {"workorder", "full"}:
        hits = retrieve_for_workorder(query)
        contexts["workorder"] = [hit.model_dump(mode="json") for hit in hits]
        rag_status["workorder"] = {"count": len(hits), "status": "ok"}
    if target == "reply":
        category_name = classification.category_name if classification else None
        hits = retrieve_for_reply(query, category_name=category_name)
        contexts["reply"] = [hit.model_dump(mode="json") for hit in hits]
        rag_status["reply"] = {"count": len(hits), "status": "ok"}

    return {
        "retrieved_contexts": contexts,
        "rag_status": rag_status,
        "next_action": "retrieve_context",
        "audit_log": append_audit(state, "retrieve_context", targets=list(rag_status)),
        "graph_trace": append_trace(state, "retrieve_context", targets=list(rag_status)),
    }


def retrieve_reply_context_node(state: CaseGraphState) -> dict:
    """分类完成后按类别召回回复依据，避免完整流程过早检索政策。"""
    query = str(state.get("transcript") or "").strip()
    classification = _classification(state)
    contexts = dict(state.get("retrieved_contexts") or {})
    rag_status = dict(state.get("rag_status") or {})
    category_name = classification.category_name if classification else None
    hits = retrieve_for_reply(query, category_name=category_name)
    contexts["reply"] = [hit.model_dump(mode="json") for hit in hits]
    rag_status["reply"] = {
        "count": len(hits),
        "status": "ok",
        "category_name": category_name,
    }
    return {
        "retrieved_contexts": contexts,
        "rag_status": rag_status,
        "next_action": "retrieve_reply_context",
        "audit_log": append_audit(
            state, "retrieve_reply_context", category_name=category_name
        ),
        "graph_trace": append_trace(
            state, "retrieve_reply_context", category_name=category_name
        ),
    }


def classify_node(state: CaseGraphState) -> dict:
    understanding = _understanding(state)
    context = _format_context(state, "classification")
    result = classify_svc.classify(
        understanding.transcript,
        understanding,
        context=context,
    )
    return {
        "classification": result.model_dump(mode="json"),
        "next_action": "classify",
        "audit_log": append_audit(state, "classify"),
        "graph_trace": append_trace(state, "classify"),
    }


def workorder_node(state: CaseGraphState) -> dict:
    understanding = _understanding(state)
    classification = _classification(state)
    context = _format_context(state, "workorder")
    result = workorder_svc.generate_work_order(
        understanding.transcript,
        understanding,
        classification,
        context=context,
    )
    return {
        "work_order": result.model_dump(mode="json"),
        "next_action": "workorder",
        "audit_log": append_audit(state, "workorder"),
        "graph_trace": append_trace(state, "workorder"),
    }


def quality_check_node(state: CaseGraphState) -> dict:
    understanding = _understanding(state)
    classification = _classification(state)
    flags: list[str] = []
    if understanding.needs_clarification:
        flags.append("missing_information")
    if understanding.urgent:
        flags.append("urgent")
    if classification and (classification.needs_manual or classification.confidence < 0.3):
        flags.append("classification_needs_manual")
    if not state.get("retrieved_contexts"):
        flags.append("no_rag_evidence")
    review_required = any(
        flag in {"missing_information", "urgent", "classification_needs_manual"}
        for flag in flags
    )
    return {
        "quality_flags": flags,
        "human_review_required": review_required,
        "next_action": "quality_check",
        "audit_log": append_audit(state, "quality_check", flags=flags),
        "graph_trace": append_trace(
            state,
            "quality_check",
            human_review_required=review_required,
        ),
    }


def reply_node(state: CaseGraphState) -> dict:
    understanding = _understanding(state)
    classification = _classification(state)
    context = _format_context(state, "reply")
    result = reply_svc.generate_reply(understanding, classification, context=context)
    return {
        "reply": result.model_dump(mode="json"),
        "next_action": "reply",
        "audit_log": append_audit(state, "reply"),
        "graph_trace": append_trace(state, "reply"),
    }


def human_review_node(state: CaseGraphState) -> dict:
    return {
        "next_action": "human_review",
        "audit_log": append_audit(
            state,
            "human_review",
            required=bool(state.get("human_review_required")),
            quality_flags=state.get("quality_flags") or [],
        ),
        "graph_trace": append_trace(
            state,
            "human_review",
            required=bool(state.get("human_review_required")),
        ),
    }


def persist_node(state: CaseGraphState) -> dict:
    graph_trace = append_trace(state, "persist")
    final_state = {**state, "graph_trace": graph_trace}
    store.save(graph_state_to_case(final_state))
    return {"graph_trace": graph_trace}



