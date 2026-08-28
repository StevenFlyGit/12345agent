"""相似历史案例接口。"""
from __future__ import annotations

from fastapi import APIRouter, Query

from app.services import history

router = APIRouter(prefix="/api/history", tags=["history"])


@router.get("")
def get_history(q: str = Query(..., description="查询文本")):
    results = history.find_similar(q, top_k=5)
    return {"query": q, "results": results}
