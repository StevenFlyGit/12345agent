"""LangGraph SQLite checkpoint 封装。"""
from __future__ import annotations

import sqlite3
import threading
from pathlib import Path

from langgraph.checkpoint.sqlite import SqliteSaver

ROOT = Path(__file__).resolve().parents[2]
CHECKPOINT_DB_PATH = ROOT / "storage" / "langgraph_checkpoints.sqlite"

_lock = threading.Lock()
_checkpointer: SqliteSaver | None = None


def get_checkpointer() -> SqliteSaver:
    """返回进程内复用的 checkpointer，按 case_id 保存图执行快照。"""
    global _checkpointer
    with _lock:
        if _checkpointer is None:
            CHECKPOINT_DB_PATH.parent.mkdir(parents=True, exist_ok=True)
            connection = sqlite3.connect(str(CHECKPOINT_DB_PATH), check_same_thread=False)
            _checkpointer = SqliteSaver(connection)
            _checkpointer.setup()
        return _checkpointer
