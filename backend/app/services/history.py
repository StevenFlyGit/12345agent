"""相似历史案例检索：基于关键词重叠与字符重合度的轻量打分。

不依赖向量库，对 18 条历史工单做相似度排序，返回 top_k。
"""
from __future__ import annotations

from app.data import loaders


def _char_set(text: str) -> set[str]:
    return set(c for c in (text or "") if not c.isspace())


def _score(text: str, candidate: str) -> float:
    a = _char_set(text)
    b = _char_set(candidate)
    if not a or not b:
        return 0.0
    union = a | b
    jaccard = len(a & b) / len(union)
    return round(jaccard, 4)


def find_similar(text: str, top_k: int = 5) -> list[dict]:
    """返回与 text 最相似的历史工单（含 source_id/category/title/request_content/handling_departments/reply_content）。"""
    cases = loaders.load_historical_cases()
    scored = []
    for c in cases:
        content = c.get("request_content", "")
        s = _score(text, content)
        scored.append((s, c))
    scored.sort(key=lambda x: x[0], reverse=True)
    result = []
    for s, c in scored[:top_k]:
        result.append(
            {
                "source_id": c.get("source_id"),
                "category": c.get("category"),
                "title": c.get("title"),
                "request_content": c.get("request_content"),
                "handling_departments": c.get("handling_departments", []),
                "reply_content": c.get("reply_content"),
                "score": s,
            }
        )
    return result
