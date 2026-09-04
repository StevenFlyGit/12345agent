"""Chroma 向量库封装。"""
from __future__ import annotations

import ctypes
import os
from pathlib import Path
from typing import Iterable

# Anaconda 3.11.3 bundles an old msvcp140.dll beside python.exe. Newer
# Chroma native extensions can load that copy first and crash the process on
# the first write. Load the current Windows runtime before importing Chroma.
if os.name == "nt":
    system_runtime = (
        Path(os.environ.get("SystemRoot", r"C:\Windows"))
        / "System32"
        / "msvcp140.dll"
    )
    if system_runtime.is_file():
        ctypes.WinDLL(str(system_runtime))

import chromadb
from langchain_core.documents import Document
from langchain_core.embeddings import Embeddings
from langchain_core.vectorstores import VectorStoreRetriever
from langchain_chroma import Chroma

from app.rag.documents import document_ids
from app.rag.embeddings import get_embedding_function

ROOT = Path(__file__).resolve().parents[2]
CHROMA_DIR = ROOT / "storage" / "chroma"

CATEGORY_COLLECTION = "category_catalog"
DEPARTMENT_COLLECTION = "department_rules"
HISTORICAL_COLLECTION = "historical_cases"
POLICY_COLLECTION = "policy_docs"

COLLECTIONS = [
    CATEGORY_COLLECTION,
    DEPARTMENT_COLLECTION,
    HISTORICAL_COLLECTION,
    POLICY_COLLECTION,
]


def get_chroma_client(persist_directory: Path | None = None):
    path = persist_directory or CHROMA_DIR
    path.mkdir(parents=True, exist_ok=True)
    return chromadb.PersistentClient(path=str(path))


def get_vectorstore(
    collection_name: str,
    *,
    embedding_function: Embeddings | None = None,
    persist_directory: Path | None = None,
) -> Chroma:
    """获取一个 Chroma collection 的 LangChain 封装。"""
    return Chroma(
        collection_name=collection_name,
        embedding_function=embedding_function or get_embedding_function(),
        persist_directory=str(persist_directory or CHROMA_DIR),
        create_collection_if_not_exists=True,
    )


def get_retriever(
    collection_name: str,
    *,
    top_k: int = 3,
    fetch_k: int = 8,
    metadata_filter: dict | None = None,
    embedding_function: Embeddings | None = None,
    persist_directory: Path | None = None,
    search_type: str = "mmr",
) -> VectorStoreRetriever:
    """返回 Chroma 的 LangChain Retriever。"""
    search_kwargs = {"k": top_k}
    if search_type == "mmr":
        search_kwargs["fetch_k"] = max(fetch_k, top_k)
    if metadata_filter:
        search_kwargs["filter"] = metadata_filter
    return get_vectorstore(
        collection_name,
        embedding_function=embedding_function,
        persist_directory=persist_directory,
    ).as_retriever(search_type=search_type, search_kwargs=search_kwargs)


def reset_collection(collection_name: str, persist_directory: Path | None = None) -> None:
    """删除指定 collection；不存在时忽略。"""
    client = get_chroma_client(persist_directory)
    try:
        client.delete_collection(collection_name)
    except Exception:
        pass


def rebuild_collection(
    collection_name: str,
    documents: list[Document],
    *,
    embedding_function: Embeddings | None = None,
    persist_directory: Path | None = None,
    reset: bool = True,
    batch_size: int = 64,
) -> int:
    """重建一个 collection 并写入文档。"""
    if reset:
        reset_collection(collection_name, persist_directory)
    if not documents:
        get_vectorstore(
            collection_name,
            embedding_function=embedding_function,
            persist_directory=persist_directory,
        )
        return 0

    store = get_vectorstore(
        collection_name,
        embedding_function=embedding_function,
        persist_directory=persist_directory,
    )
    ids = document_ids(collection_name, documents)
    for start in range(0, len(documents), batch_size):
        end = start + batch_size
        store.add_documents(documents[start:end], ids=ids[start:end])
    return len(documents)


def collection_count(
    collection_name: str,
    *,
    persist_directory: Path | None = None,
) -> int:
    """返回 collection 文档数量；不存在则为 0。"""
    client = get_chroma_client(persist_directory)
    try:
        return client.get_collection(collection_name).count()
    except Exception:
        return 0


def collection_counts(
    collection_names: Iterable[str] = COLLECTIONS,
    *,
    persist_directory: Path | None = None,
) -> dict[str, int]:
    return {
        name: collection_count(name, persist_directory=persist_directory)
        for name in collection_names
    }
