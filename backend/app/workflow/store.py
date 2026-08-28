"""SQLite 案件存储（标准库实现，线程锁保证简单并发安全）。

库文件位于 storage/cases.db，表 cases(case_id PK, created_at, data JSON)。
所有访问经模块级锁串行化，避免并发写冲突。
"""
from __future__ import annotations

import json
import threading
from pathlib import Path

from app.schemas.models import CaseState

# 项目根
ROOT = Path(__file__).resolve().parents[2]
DB_PATH = ROOT / "storage" / "cases.db"

_lock = threading.Lock()


def _connect():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    import sqlite3

    conn = sqlite3.connect(str(DB_PATH), check_same_thread=False)
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS cases (
            case_id TEXT PRIMARY KEY,
            created_at TEXT,
            data TEXT
        )
        """
    )
    conn.commit()
    return conn


def save(case: CaseState) -> None:
    with _lock:
        conn = _connect()
        try:
            conn.execute(
                "INSERT OR REPLACE INTO cases (case_id, created_at, data) VALUES (?, ?, ?)",
                (case.case_id, case.created_at, case.model_dump_json()),
            )
            conn.commit()
        finally:
            conn.close()


def get(case_id: str) -> CaseState | None:
    with _lock:
        conn = _connect()
        try:
            cur = conn.execute("SELECT data FROM cases WHERE case_id = ?", (case_id,))
            row = cur.fetchone()
        finally:
            conn.close()
    if not row:
        return None
    return CaseState.model_validate_json(row[0])


def list() -> list[CaseState]:
    with _lock:
        conn = _connect()
        try:
            cur = conn.execute("SELECT data FROM cases ORDER BY created_at DESC")
            rows = cur.fetchall()
        finally:
            conn.close()
    return [CaseState.model_validate_json(r[0]) for r in rows]
