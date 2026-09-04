from __future__ import annotations

import json

from langchain_core.documents import Document
from langchain_core.embeddings import Embeddings

from app.rag.documents import (
    build_category_documents,
    build_department_rule_documents,
    build_historical_case_documents,
)
from app.rag.policy_loaders import load_policy_documents, load_raw_policy_documents, validate_policy_sources
from app.rag.retrievers import search_collection
from app.rag.schemas import EvidenceItem
from app.rag.vectorstore import collection_count, get_vectorstore, rebuild_collection


class TinyEmbeddings(Embeddings):
    """测试用稳定 embedding，避免单元测试加载真实模型。"""

    def _embed(self, text: str) -> list[float]:
        return [float(len(text)), float(sum(ord(c) for c in text) % 997)]

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        return [self._embed(text) for text in texts]

    def embed_query(self, text: str) -> list[float]:
        return self._embed(text)


def test_build_official_documents():
    assert len(build_category_documents()) == 12
    assert len(build_department_rule_documents()) == 12
    assert len(build_historical_case_documents()) > 0


def test_rebuild_collection_with_fake_embeddings(tmp_path):
    docs = [
        Document(
            page_content="市场监管 食品经营许可 投诉处理",
            metadata={"doc_type": "test", "category_name": "市场监管"},
        ),
        Document(
            page_content="公交站点 被社会车辆占用",
            metadata={"doc_type": "test", "category_name": "交通运输"},
        ),
    ]

    count = rebuild_collection(
        "test_collection",
        docs,
        embedding_function=TinyEmbeddings(),
        persist_directory=tmp_path,
    )

    assert count == 2
    assert collection_count("test_collection", persist_directory=tmp_path) == 2

    store = get_vectorstore(
        "test_collection",
        embedding_function=TinyEmbeddings(),
        persist_directory=tmp_path,
    )
    results = store.similarity_search("食品经营", k=1)
    assert results
    assert results[0].metadata["doc_type"] == "test"


def test_policy_source_validation(tmp_path):
    policy = tmp_path / "policy.md"
    policy.write_text("测试政策正文", encoding="utf-8")

    issues = validate_policy_sources(tmp_path)
    assert any("缺少同名 .meta.json" in issue.message for issue in issues)

    meta = tmp_path / "policy.meta.json"
    meta.write_text(
        json.dumps(
            {
                "source_name": "测试政策",
                "publisher": "测试部门",
                "category_name": "城乡建设",
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    assert validate_policy_sources(tmp_path) == []




def test_policy_loader_uses_langchain_loader_and_splitter(tmp_path):
    policy = tmp_path / "policy.md"
    policy.write_text(
        "# 测试政策\n" + "物业维修资金申请流程。" * 120,
        encoding="utf-8",
    )
    meta = tmp_path / "policy.meta.json"
    meta.write_text(
        json.dumps(
            {
                "source_name": "测试政策",
                "source_url": "https://example.com/policy",
                "publisher": "测试部门",
                "published_at": "2026-01-01",
                "collected_at": "2026-09-03",
                "category_name": "城乡建设",
                "doc_type": "policy",
                "sensitive_level": "public_demo",
                "usage_scope": "仅用于测试",
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    raw_docs = load_raw_policy_documents(tmp_path)
    assert len(raw_docs) == 1
    assert raw_docs[0].metadata["loader"] == "TextLoader"
    assert raw_docs[0].metadata["is_chunk"] is False
    assert raw_docs[0].metadata["original_doc_id"]

    chunk_docs = load_policy_documents(tmp_path)
    assert len(chunk_docs) > 1
    assert all(doc.metadata["is_chunk"] is True for doc in chunk_docs)
    assert all(doc.metadata["original_doc_id"] == raw_docs[0].metadata["original_doc_id"] for doc in chunk_docs)
    assert chunk_docs[0].metadata["chunk_count"] == len(chunk_docs)


def test_search_collection_returns_evidence_from_langchain_retriever(tmp_path):
    docs = [
        Document(
            page_content="市场监管 食品经营许可 投诉处理",
            metadata={
                "doc_type": "policy",
                "source_name": "测试政策",
                "source_url": "https://example.com/market",
                "category_name": "市场监管",
            },
        ),
        Document(
            page_content="公交站点 被社会车辆占用",
            metadata={"doc_type": "policy", "category_name": "交通运输"},
        ),
    ]
    rebuild_collection(
        "test_retriever_collection",
        docs,
        embedding_function=TinyEmbeddings(),
        persist_directory=tmp_path,
    )

    results = search_collection(
        "test_retriever_collection",
        "食品经营许可",
        top_k=1,
        metadata_filter={"category_name": "市场监管"},
        search_type="similarity",
        embedding_function=TinyEmbeddings(),
        persist_directory=tmp_path,
    )

    assert len(results) == 1
    assert isinstance(results[0], EvidenceItem)
    assert results[0].collection == "test_retriever_collection"
    assert results[0].doc_type == "policy"
    assert results[0].source_name == "测试政策"
    assert results[0].source_url == "https://example.com/market"
