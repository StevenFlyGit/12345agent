"""数据加载器：统一读取分类目录、部门规则、历史工单样例、mock 样例。

所有路径以本文件所在目录向上两级定位到项目根，确保相对路径在任何调用位置都正确。
使用模块级缓存避免重复读盘。
"""
from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Any

# 项目根：app/data/loaders.py -> parents[0]=data, parents[1]=app, parents[2]=根
ROOT = Path(__file__).resolve().parents[2]


def _read_json(path: Path) -> Any:
    with path.open(encoding="utf-8") as f:
        return json.load(f)


@lru_cache(maxsize=1)
def load_category_catalog() -> dict:
    """加载分类目录（含 12 类 code/name）。"""
    path = ROOT / "data" / "categories" / "category_catalog.json"
    return _read_json(path)


@lru_cache(maxsize=1)
def load_department_rules() -> dict:
    """加载部门职责规则（含 12 类 rules 数组）。"""
    path = ROOT / "data" / "departments" / "department_rules.json"
    return _read_json(path)


@lru_cache(maxsize=1)
def load_historical_cases() -> list[dict]:
    """读取 work_orders.json。

    该文件为「多个 JSON 对象首尾相接、无数组包裹」的格式（非 NDJSON、非整体数组），
    使用 raw_decode 逐个解析，避免逐行解析把内部字符串当成记录。
    """
    path = ROOT / "data" / "processed" / "work_orders.json"
    cases: list[dict] = []
    if not path.exists():
        return cases
    text = path.read_text(encoding="utf-8")
    decoder = json.JSONDecoder()
    idx = 0
    n = len(text)
    while idx < n:
        # 跳过空白
        while idx < n and text[idx] in " \t\r\n":
            idx += 1
        if idx >= n:
            break
        try:
            obj, end = decoder.raw_decode(text, idx)
        except json.JSONDecodeError:
            break
        if isinstance(obj, dict):
            cases.append(obj)
        idx = end
    return cases


@lru_cache(maxsize=1)
def load_mock_requests() -> list[dict]:
    """读取 mock_requests.json（8 条示例文本）。"""
    path = ROOT / "data" / "mock" / "mock_requests.json"
    return _read_json(path)


@lru_cache(maxsize=1)
def load_expected_results() -> list[dict]:
    path = ROOT / "data" / "mock" / "expected_results.json"
    return _read_json(path)


def category_name_to_code() -> dict[str, str]:
    """中文类别名 -> code 映射。"""
    mapping: dict[str, str] = {}
    for item in load_category_catalog().get("categories", []):
        mapping[item["name"]] = item["code"]
    return mapping


def category_code_to_name() -> dict[str, str]:
    """code -> 中文类别名 映射。"""
    return {v: k for k, v in category_name_to_code().items()}


if __name__ == "__main__":
    print("ROOT:", ROOT)
    print("categories:", len(load_category_catalog().get("categories", [])))
    print("department rules:", len(load_department_rules().get("rules", [])))
    print("historical cases:", len(load_historical_cases()))
    print("mock requests:", len(load_mock_requests()))
