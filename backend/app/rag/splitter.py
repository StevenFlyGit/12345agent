"""LangChain 文档分片封装。"""
from __future__ import annotations

from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter

from app.rag.documents import _safe_metadata

DEFAULT_CHUNK_SIZE = 800
DEFAULT_CHUNK_OVERLAP = 120
CHINESE_SEPARATORS = [
    "\n\n",
    "\n",
    "。",
    "！",
    "？",
    "；",
    ";",
    "，",
    ",",
    "、",
    " ",
    "",
]


def get_text_splitter(
    *,
    chunk_size: int = DEFAULT_CHUNK_SIZE,
    chunk_overlap: int = DEFAULT_CHUNK_OVERLAP,
) -> RecursiveCharacterTextSplitter:
    """返回适合中文政务文本的 RecursiveCharacterTextSplitter。"""
    return RecursiveCharacterTextSplitter(
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
        separators=CHINESE_SEPARATORS,
    )


def split_documents(
    documents: list[Document],
    *,
    collection_name: str,
    chunk_size: int = DEFAULT_CHUNK_SIZE,
    chunk_overlap: int = DEFAULT_CHUNK_OVERLAP,
) -> list[Document]:
    """将加载后的原始 Document 分片，并补齐 chunk 元数据。"""
    if not documents:
        return []

    splitter = get_text_splitter(
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
    )
    result: list[Document] = []
    for document in documents:
        chunks = splitter.split_documents([document])
        chunk_count = len(chunks)
        for index, chunk in enumerate(chunks):
            metadata = {
                **chunk.metadata,
                "collection": collection_name,
                "chunk_index": index,
                "chunk_count": chunk_count,
                "is_chunk": True,
            }
            result.append(
                Document(
                    page_content=chunk.page_content,
                    metadata=_safe_metadata(metadata),
                )
            )
    return result
