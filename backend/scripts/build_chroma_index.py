"""构建 Chroma RAG 索引。

用法：
  python scripts/build_chroma_index.py --source official
  python scripts/build_chroma_index.py --source policies
  python scripts/build_chroma_index.py --source all
"""
from __future__ import annotations

from pathlib import Path
import sys

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

import argparse

from app.rag.documents import build_official_documents
from app.rag.embeddings import resolve_embedding_model
from app.rag.policy_loaders import load_policy_documents, validate_policy_sources
from app.rag.vectorstore import (
    POLICY_COLLECTION,
    collection_counts,
    rebuild_collection,
)


def build_official(reset: bool) -> dict[str, int]:
    docs_by_collection = build_official_documents()
    counts: dict[str, int] = {}
    for collection_name, documents in docs_by_collection.items():
        counts[collection_name] = rebuild_collection(
            collection_name,
            documents,
            reset=reset,
        )
    return counts


def build_policies(reset: bool) -> dict[str, int]:
    issues = validate_policy_sources()
    for issue in issues:
        print(f"[{issue.level}] {issue.file}: {issue.message}")

    documents = load_policy_documents()
    return {
        POLICY_COLLECTION: rebuild_collection(
            POLICY_COLLECTION,
            documents,
            reset=reset,
        )
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="构建 Chroma RAG 索引")
    parser.add_argument(
        "--source",
        choices=["official", "policies", "all"],
        default="official",
        help="索引来源：官方数据、自采政策文件或全部",
    )
    parser.add_argument(
        "--no-reset",
        action="store_true",
        help="不删除原 collection，直接追加写入",
    )
    args = parser.parse_args()

    reset = not args.no_reset
    print(f"Embedding 模型：{resolve_embedding_model()}")

    written: dict[str, int] = {}
    if args.source in {"official", "all"}:
        written.update(build_official(reset=reset))
    if args.source in {"policies", "all"}:
        written.update(build_policies(reset=reset))

    print("写入结果：")
    for name, count in written.items():
        print(f"- {name}: {count}")

    print("当前 collection 数量：")
    for name, count in collection_counts().items():
        print(f"- {name}: {count}")


if __name__ == "__main__":
    main()

