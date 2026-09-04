"""中文政务文档分片封装。"""
from __future__ import annotations

from langchain_core.documents import Document

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
]


class ChineseTextSplitter:
    """按中文自然边界切分文本，并保留相邻分片重叠内容。"""

    def __init__(self, *, chunk_size: int, chunk_overlap: int):
        if chunk_size <= 0:
            raise ValueError("chunk_size 必须大于 0")
        if chunk_overlap < 0 or chunk_overlap >= chunk_size:
            raise ValueError("chunk_overlap 必须大于等于 0 且小于 chunk_size")
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap

    def split_text(self, text: str) -> list[str]:
        normalized = text.strip()
        if not normalized:
            return []

        chunks: list[str] = []
        start = 0
        text_length = len(normalized)
        while start < text_length:
            end = min(start + self.chunk_size, text_length)
            if end < text_length:
                minimum_break = start + self.chunk_size // 2
                for separator in CHINESE_SEPARATORS:
                    position = normalized.rfind(separator, minimum_break, end)
                    if position >= minimum_break:
                        end = position + len(separator)
                        break

            chunk = normalized[start:end].strip()
            if chunk:
                chunks.append(chunk)
            if end >= text_length:
                break
            start = max(start + 1, end - self.chunk_overlap)
        return chunks

    def split_documents(self, documents: list[Document]) -> list[Document]:
        result: list[Document] = []
        for document in documents:
            for chunk in self.split_text(document.page_content):
                result.append(
                    Document(
                        page_content=chunk,
                        metadata=dict(document.metadata),
                    )
                )
        return result


def get_text_splitter(
    *,
    chunk_size: int = DEFAULT_CHUNK_SIZE,
    chunk_overlap: int = DEFAULT_CHUNK_OVERLAP,
) -> ChineseTextSplitter:
    """返回适合中文政务文本的轻量字符分块器。"""
    return ChineseTextSplitter(
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
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
