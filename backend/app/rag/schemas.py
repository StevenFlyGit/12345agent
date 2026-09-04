"""RAG 层内部数据模型。"""
from __future__ import annotations

from pydantic import BaseModel, Field


class EvidenceItem(BaseModel):
    """标准化检索证据，可给 LLM、LangGraph state、前端和人工审核共用。"""

    collection: str
    doc_type: str = ""
    source_name: str = ""
    source_url: str = ""
    content: str
    score: float | None = None
    metadata: dict = Field(default_factory=dict)


class RagHit(EvidenceItem):
    """兼容旧命名；后续统一使用 EvidenceItem。"""


class RagWorkflowContext(BaseModel):
    """为后续 LangGraph state 预留的 RAG 字段结构。"""

    retrieved_contexts: dict[str, list[EvidenceItem]] = Field(default_factory=dict)
    rag_status: dict = Field(default_factory=dict)


class PolicySourceMeta(BaseModel):
    """自采政府文件配套的元数据。"""

    source_name: str
    source_url: str | None = None
    publisher: str
    published_at: str | None = None
    collected_at: str | None = None
    category_name: str
    doc_type: str = "policy"
    sensitive_level: str = "public_demo"
    usage_scope: str | None = None
    version: str = "manual"


class PolicyValidationIssue(BaseModel):
    """自采文件校验问题。"""

    file: str
    level: str = "error"
    message: str
