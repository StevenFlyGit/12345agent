"""StateGraph 组装与同步调用入口。"""
from __future__ import annotations

from functools import lru_cache
from typing import Any

from langgraph.graph import END, START, StateGraph

from app.graph import edges, nodes
from app.graph.checkpoints import get_checkpointer
from app.graph.state import CaseGraphState, case_to_graph_state, graph_state_to_case
from app.schemas.models import CaseState


def build_case_graph(checkpointer: Any | None = None):
    """构建案件图；测试可传入临时 checkpointer 或 None。"""
    builder = StateGraph(CaseGraphState)
    builder.add_node("prepare_input", nodes.prepare_input_node)
    builder.add_node("understand", nodes.understand_node)
    builder.add_node("retrieve_context", nodes.retrieve_context_node)
    builder.add_node("classify", nodes.classify_node)
    builder.add_node("retrieve_reply_context", nodes.retrieve_reply_context_node)
    builder.add_node("workorder", nodes.workorder_node)
    builder.add_node("quality_check", nodes.quality_check_node)
    builder.add_node("reply", nodes.reply_node)
    builder.add_node("human_review", nodes.human_review_node)
    builder.add_node("persist", nodes.persist_node)

    builder.add_edge(START, "prepare_input")
    builder.add_edge("prepare_input", "understand")
    builder.add_conditional_edges(
        "understand",
        edges.route_after_understand,
        {"retrieve_context": "retrieve_context", "persist": "persist"},
    )
    builder.add_conditional_edges(
        "retrieve_context",
        edges.route_after_retrieve,
        {"classify": "classify", "reply": "reply"},
    )
    builder.add_conditional_edges(
        "classify",
        edges.route_after_classify,
        {"workorder": "workorder", "persist": "persist"},
    )
    builder.add_conditional_edges(
        "workorder",
        edges.route_after_workorder,
        {"quality_check": "quality_check", "persist": "persist"},
    )
    builder.add_conditional_edges(
        "quality_check",
        edges.route_after_quality_check,
        {"retrieve_reply_context": "retrieve_reply_context", "human_review": "human_review"},
    )
    builder.add_edge("retrieve_reply_context", "reply")
    builder.add_conditional_edges(
        "reply",
        edges.route_after_reply,
        {"persist": "persist", "human_review": "human_review"},
    )
    builder.add_edge("human_review", "persist")
    builder.add_edge("persist", END)
    return builder.compile(checkpointer=checkpointer)


@lru_cache(maxsize=1)
def get_case_graph():
    return build_case_graph(checkpointer=get_checkpointer())


def run_case_graph(
    case: CaseState,
    *,
    target_stage: str,
    transcript: str | None = None,
    transcript_source: str | None = None,
) -> CaseState:
    """按指定阶段执行图，并以 case_id 作为 LangGraph thread_id。"""
    state = case_to_graph_state(case, target_stage)
    if transcript is not None:
        state["transcript"] = transcript
    if transcript_source is not None:
        state["transcript_source"] = transcript_source
    result = get_case_graph().invoke(
        state,
        config={"configurable": {"thread_id": case.case_id}},
    )
    return graph_state_to_case(result)


