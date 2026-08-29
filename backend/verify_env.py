import importlib
import platform
import sqlite3
import sys

MODULES = [
    # Agent、数据结构与配置
    "langgraph",
    "langgraph.checkpoint.sqlite",
    "langchain",
    "pydantic",
    "pydantic_settings",
    "dotenv",
    "tenacity",
    "orjson",
    "aiosqlite",
    # Excel 与业务数据处理
    "pandas",
    "openpyxl",
    # 后端 API
    "fastapi",
    "uvicorn",
    "multipart",
    # 大模型：OpenAI 或兼容接口
    "openai",
    "langchain_openai",
    # 录音转写
    "faster_whisper",
    # RAG 与检索
    "qdrant_client",
    "sentence_transformers",
    "rank_bm25",
    # 快速演示界面
    "streamlit",
    # 测试
    "pytest",
    "pytest_asyncio",
    "httpx",
]

print("Python:", sys.version)
print("System:", platform.platform())
print("SQLite:", sqlite3.sqlite_version)

failed = []
for name in MODULES:
    try:
        importlib.import_module(name)
        print(f"[OK] {name}")
    except Exception as exc:
        failed.append(name)
        print(f"[FAIL] {name}: {exc}")

if failed:
    raise SystemExit(f"Environment check failed: {failed}")

print("Environment check passed.")
