"""部门规则文件的读取、原子更新与 RAG 索引同步。"""
from __future__ import annotations

import json
import os
import tempfile
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from app.data import loaders
from app.rag.documents import build_department_rule_documents
from app.rag.vectorstore import DEPARTMENT_COLLECTION, rebuild_collection

RULES_PATH = loaders.ROOT / "data" / "departments" / "department_rules.json"
EDITABLE_FIELDS = (
    "category_name",
    "department",
    "co_departments",
    "keywords",
    "responsibilities",
)

_lock = threading.RLock()


class RuleNotFoundError(LookupError):
    """请求的 category_code 不存在。"""


class RuleSyncError(RuntimeError):
    """规则文件或检索索引同步失败。"""


def _read_unlocked() -> dict[str, Any]:
    with RULES_PATH.open(encoding="utf-8") as source:
        document = json.load(source)
    if not isinstance(document, dict) or not isinstance(document.get("rules"), list):
        raise RuleSyncError("department_rules.json 数据结构无效")
    return document


def _atomic_write(document: dict[str, Any]) -> None:
    RULES_PATH.parent.mkdir(parents=True, exist_ok=True)
    temp_path: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            newline="\n",
            dir=RULES_PATH.parent,
            prefix=f".{RULES_PATH.stem}.",
            suffix=".tmp",
            delete=False,
        ) as target:
            json.dump(document, target, ensure_ascii=False, indent=2)
            target.write("\n")
            target.flush()
            os.fsync(target.fileno())
            temp_path = Path(target.name)
        os.replace(temp_path, RULES_PATH)
    finally:
        if temp_path is not None and temp_path.exists():
            temp_path.unlink(missing_ok=True)


def _updated_at() -> str:
    return datetime.fromtimestamp(
        RULES_PATH.stat().st_mtime, tz=timezone.utc
    ).isoformat()


def _sync_index() -> int:
    loaders.load_department_rules.cache_clear()
    documents = build_department_rule_documents()
    return rebuild_collection(
        DEPARTMENT_COLLECTION,
        documents,
        reset=True,
    )


def _write_and_sync(
    original: dict[str, Any], updated: dict[str, Any]
) -> int:
    _atomic_write(updated)
    try:
        return _sync_index()
    except Exception as exc:
        # 索引更新失败时恢复原文件，避免“接口报错但规则已变更”的半成功状态。
        _atomic_write(original)
        loaders.load_department_rules.cache_clear()
        try:
            _sync_index()
        except Exception:
            pass
        raise RuleSyncError(
            "部门规则检索索引更新失败，本次文件修改已回滚"
        ) from exc


def get_document() -> dict[str, Any]:
    with _lock:
        document = _read_unlocked()
        return {
            **document,
            "filename": RULES_PATH.name,
            "updated_at": _updated_at(),
        }


def update_rule(code: str, changes: dict[str, Any]) -> dict[str, Any]:
    with _lock:
        original = _read_unlocked()
        updated = json.loads(json.dumps(original, ensure_ascii=False))
        target: dict[str, Any] | None = None

        for rule in updated["rules"]:
            if rule.get("category_code") == code:
                target = rule
                break
        if target is None:
            raise RuleNotFoundError(f"部门规则不存在：{code}")

        for field in EDITABLE_FIELDS:
            if field in changes:
                value = changes[field]
                if isinstance(value, str):
                    value = value.strip()
                elif isinstance(value, list):
                    value = list(dict.fromkeys(str(item).strip() for item in value if str(item).strip()))
                target[field] = value

        for required in ("category_name", "department", "responsibilities"):
            if not target.get(required):
                raise ValueError(f"{required} 不能为空")

        index_count = _write_and_sync(original, updated)
        return {
            "rule": target,
            "updated_at": _updated_at(),
            "index_count": index_count,
        }


def delete_rule(code: str) -> dict[str, Any]:
    with _lock:
        original = _read_unlocked()
        updated = json.loads(json.dumps(original, ensure_ascii=False))
        before = len(updated["rules"])
        updated["rules"] = [
            rule for rule in updated["rules"]
            if rule.get("category_code") != code
        ]
        if len(updated["rules"]) == before:
            raise RuleNotFoundError(f"部门规则不存在：{code}")

        index_count = _write_and_sync(original, updated)
        return {
            "deleted_code": code,
            "rules_count": len(updated["rules"]),
            "updated_at": _updated_at(),
            "index_count": index_count,
        }
