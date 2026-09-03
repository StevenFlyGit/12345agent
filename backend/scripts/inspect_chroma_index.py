"""检查 Chroma RAG 索引。"""
from __future__ import annotations

from pathlib import Path
import sys

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

import argparse

from app.rag.retrievers import search_collection
from app.rag.vectorstore import COLLECTIONS, collection_counts


def main() -> None:
    parser = argparse.ArgumentParser(description="检查 Chroma collection 数量和检索结果")
    parser.add_argument("--query", default="", help="可选检索文本")
    parser.add_argument("--collection", choices=COLLECTIONS, default="historical_cases")
    parser.add_argument("--top-k", type=int, default=3)
    args = parser.parse_args()

    print("当前 collection 数量：")
    for name, count in collection_counts().items():
        print(f"- {name}: {count}")

    if args.query:
        print(f"\n检索 collection={args.collection}, query={args.query}")
        for hit in search_collection(args.collection, args.query, top_k=args.top_k):
            source = hit.metadata.get("source_name") or hit.metadata.get("source_file")
            print("-" * 60)
            print(f"score: {hit.score}")
            print(f"source: {source}")
            print(hit.content[:500])


if __name__ == "__main__":
    main()

