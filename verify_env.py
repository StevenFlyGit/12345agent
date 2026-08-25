import importlib
import platform
import sqlite3
import sys

MODULES = [
    "langgraph",
    "pydantic",
    "dotenv",
    "pandas",
    "openpyxl",
    "fastapi",
    "uvicorn",
    "openai",
    "faster_whisper",
    "qdrant_client",
    "sentence_transformers",
    "rank_bm25",
    "streamlit",
    "pytest",
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
