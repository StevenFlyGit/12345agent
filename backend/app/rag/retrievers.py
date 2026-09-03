"""RAG 检索器封装。"""
from __future__ import annotations

from pathlib import Path

from langchain_core.documents import Document
from langchain_core.embeddings import Embeddings

from app.rag.schemas import EvidenceItem, RagHit
from app.rag.vectorstore import (
    CATEGORY_COLLECTION,
    DEPARTMENT_COLLECTION,
    HISTORICAL_COLLECTION,
    POLICY_COLLECTION,
    get_retriever,
)


def _document_to_evidence(collection_name: str, document: Document) -> EvidenceItem:
    metadata = dict(document.metadata)
    return EvidenceItem(
        collection=collection_name,
        doc_type=str(metadata.get("doc_type") or ""),
        source_name=str(metadata.get("source_name") or metadata.get("source_file") or ""),
        source_url=str(metadata.get("source_url") or ""),
        content=document.page_content,
        score=None,
        metadata=metadata,
    )


def search_collection(
    collection_name: str,
    query: str,
    *,
    top_k: int = 3,
    metadata_filter: dict | None = None,
    search_type: str = "mmr",
    embedding_function: Embeddings | None = None,
    persist_directory: Path | None = None,
) -> list[EvidenceItem]:
    """使用 LangChain Retriever 检索指定 Chroma collection。"""
    if not query.strip():
        return []
    try:
        retriever = get_retriever(
            collection_name,
            top_k=top_k,
            metadata_filter=metadata_filter,
            search_type=search_type,
            embedding_function=embedding_function,
            persist_directory=persist_directory,
        )
        documents = retriever.invoke(query)
    except Exception:
        return []

    return [_document_to_evidence(collection_name, doc) for doc in documents]


def retrieve_category_context(query: str, top_k: int = 3) -> list[EvidenceItem]:
    return search_collection(CATEGORY_COLLECTION, query, top_k=top_k)


def retrieve_department_context(
    query: str,
    *,
    category_name: str | None = None,
    top_k: int = 3,
) -> list[EvidenceItem]:
    metadata_filter = {"category_name": category_name} if category_name else None
    return search_collection(
        DEPARTMENT_COLLECTION,
        query,
        top_k=top_k,
        metadata_filter=metadata_filter,
    )


def retrieve_historical_cases(query: str, top_k: int = 3) -> list[EvidenceItem]:
    return search_collection(HISTORICAL_COLLECTION, query, top_k=top_k)


def retrieve_policy_context(
    query: str,
    *,
    category_name: str | None = None,
    top_k: int = 3,
) -> list[EvidenceItem]:
    metadata_filter = {"category_name": category_name} if category_name else None
    return search_collection(
        POLICY_COLLECTION,
        query,
        top_k=top_k,
        metadata_filter=metadata_filter,
    )


def retrieve_for_classification(query: str, top_k: int = 3) -> list[EvidenceItem]:
    """分类阶段使用：事项类别 + 部门职责 + 少量历史案例。"""
    return (
        retrieve_category_context(query, top_k=top_k)
        + retrieve_department_context(query, top_k=top_k)
        + retrieve_historical_cases(query, top_k=2)
    )


def retrieve_for_workorder(query: str, top_k: int = 3) -> list[EvidenceItem]:
    """工单生成阶段使用：相似历史工单。"""
    return retrieve_historical_cases(query, top_k=top_k)


def retrieve_for_reply(
    query: str,
    *,
    category_name: str | None = None,
    top_k: int = 3,
) -> list[EvidenceItem]:
    """回复阶段使用：历史工单 + 政策文件。"""
    return retrieve_historical_cases(query, top_k=top_k) + retrieve_policy_context(
        query,
        category_name=category_name,
        top_k=top_k,
    )


def format_hits_for_prompt(hits: list[EvidenceItem] | list[RagHit], max_chars: int = 1800) -> str:
    """将检索证据整理为可放入 Prompt 的上下文。"""
    if not hits:
        return "无"

    blocks: list[str] = []
    total = 0
    for index, hit in enumerate(hits, start=1):
        source = hit.source_name or hit.metadata.get("source_file") or hit.collection
        category = hit.metadata.get("category_name") or ""
        department = hit.metadata.get("department") or ""
        source_url = hit.source_url or hit.metadata.get("source_url") or ""
        header = f"[{index}] collection={hit.collection} doc_type={hit.doc_type} source={source}"
        if source_url:
            header += f" url={source_url}"
        if category:
            header += f" category={category}"
        if department:
            header += f" department={department}"
        body = hit.content.strip()
        block = f"{header}\n{body}"
        if total + len(block) > max_chars:
            break
        blocks.append(block)
        total += len(block)
    return "\n\n".join(blocks) if blocks else "无"
