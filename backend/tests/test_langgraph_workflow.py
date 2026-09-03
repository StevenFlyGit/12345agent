"""LangGraph 编排回归测试：不依赖本地 Chroma 索引或 LLM Key。"""
from __future__ import annotations

from fastapi.testclient import TestClient

from app.graph import nodes
from app.rag.schemas import EvidenceItem
from app.services import local_engine
from app.workflow import orchestrator, store
from app.main import app


TEXT = "南陵县某理发店没有公示服务价格，也没有在醒目位置悬挂营业执照，希望有关部门核查。"


def _evidence(collection: str, doc_type: str) -> list[EvidenceItem]:
    return [
        EvidenceItem(
            collection=collection,
            doc_type=doc_type,
            source_name="LangGraph 测试知识",
            content="用于验证检索结果会写入图状态并传给后续业务节点。",
            score=0.1,
            metadata={"source_id": "test-001"},
        )
    ]


def _patch_retrievers(monkeypatch) -> None:
    monkeypatch.setattr(
        nodes,
        "retrieve_for_classification",
        lambda query: _evidence("category_catalog", "category"),
    )
    monkeypatch.setattr(
        nodes,
        "retrieve_for_workorder",
        lambda query: _evidence("historical_cases", "historical_case"),
    )
    monkeypatch.setattr(
        nodes,
        "retrieve_for_reply",
        lambda query, category_name=None: _evidence("policy_docs", "policy"),
    )


def test_langgraph_keeps_staged_api_contract(monkeypatch):
    """原有分阶段接口在 LangGraph 模式下保持可用，并留下 RAG / 图轨迹。"""
    _patch_retrievers(monkeypatch)
    original_classify = nodes.classify_svc.classify

    def classify_with_confident_result(*args, **kwargs):
        result = original_classify(*args, **kwargs)
        return result.model_copy(
            update={"confidence": 0.9, "needs_manual": False, "manual_hint": None}
        )

    monkeypatch.setattr(
        nodes.classify_svc, "classify", classify_with_confident_result
    )
    monkeypatch.setattr(orchestrator, "get_workflow_engine", lambda: "langgraph")

    client = TestClient(app)
    created = client.post("/api/cases", json={"text": TEXT})
    assert created.status_code == 200
    case_id = created.json()["case_id"]
    assert created.json()["understanding"]["source"] == "local-engine"

    classified = client.post(f"/api/cases/{case_id}/classify")
    assert classified.status_code == 200
    assert classified.json()["category_name"] == "市场监管"

    work_order = client.post(f"/api/cases/{case_id}/workorder")
    assert work_order.status_code == 200
    assert work_order.json()["suggested_category"] == "市场监管"

    completed = orchestrator.run_full_workflow(case_id)
    assert completed.reply is not None
    assert completed.rag_status["reply"]["category_name"] == "市场监管"
    assert "retrieve_reply_context" in {
        item["node"] for item in completed.graph_trace
    }

    detail = client.get(f"/api/cases/{case_id}").json()
    assert detail["rag_status"]["classification"]["count"] == 1
    assert detail["rag_status"]["workorder"]["count"] == 1
    assert {item["node"] for item in detail["graph_trace"]} >= {
        "prepare_input",
        "understand",
        "retrieve_context",
        "classify",
        "workorder",
        "persist",
    }


def test_langgraph_routes_urgent_case_to_human_review(monkeypatch):
    """完整图对紧急案件应跳过自动回复，进入人工复核节点。"""
    _patch_retrievers(monkeypatch)
    monkeypatch.setattr(orchestrator, "get_workflow_engine", lambda: "langgraph")

    case = orchestrator.create_case(text="南陵县某小区楼道发生燃气泄漏，请立即安排人员处置。")
    result = orchestrator.run_full_workflow(case.case_id)

    assert "urgent" in result.quality_flags
    assert result.human_review_required is True
    assert result.reply is None
    assert result.next_action == "human_review"
    assert {item["node"] for item in result.graph_trace} >= {
        "retrieve_context",
        "classify",
        "workorder",
        "quality_check",
        "human_review",
        "persist",
    }
    persisted = store.get(case.case_id)
    assert persisted is not None
    assert persisted.human_review_required is True


