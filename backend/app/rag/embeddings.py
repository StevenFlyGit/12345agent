"""Embedding 模型封装。

默认优先加载项目内本地模型：
`backend/storage/models/bge-small-zh-v1.5`。
"""
from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from langchain_core.embeddings import Embeddings
from app.config import settings

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_LOCAL_MODEL = ROOT / "storage" / "models" / "bge-small-zh-v1.5"
DEFAULT_REMOTE_MODEL = "BAAI/bge-small-zh-v1.5"


def resolve_embedding_model() -> str:
    """解析 embedding 模型配置，支持项目内相对路径。"""
    configured = (settings.EMBEDDING_MODEL or "").strip()
    if configured and configured != "replace_me":
        path = Path(configured)
        if not path.is_absolute():
            path = ROOT / path
        return str(path if path.exists() else configured)
    if DEFAULT_LOCAL_MODEL.exists():
        return str(DEFAULT_LOCAL_MODEL)
    return DEFAULT_REMOTE_MODEL


class SentenceTransformerEmbeddings(Embeddings):
    """让 sentence-transformers 适配 LangChain Embeddings 接口。"""

    def __init__(self, model_name: str | None = None):
        # 延迟加载重量级依赖，普通 API 启动和不使用向量模型的测试无需初始化 torch。
        from sentence_transformers import SentenceTransformer

        self.model_name = model_name or resolve_embedding_model()
        self.model = SentenceTransformer(self.model_name)

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        vectors = self.model.encode(
            texts,
            normalize_embeddings=True,
            show_progress_bar=False,
        )
        return vectors.tolist()

    def embed_query(self, text: str) -> list[float]:
        return self.embed_documents([text])[0]


@lru_cache(maxsize=1)
def get_embedding_function() -> SentenceTransformerEmbeddings:
    """缓存 embedding 模型，避免每次检索重复加载。"""
    return SentenceTransformerEmbeddings()

