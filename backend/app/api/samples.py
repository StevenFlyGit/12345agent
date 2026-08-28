"""样例接口：返回 mock 文本样例 + 可从历史工单抽取的样例录音。"""
from __future__ import annotations

from fastapi import APIRouter

from app.data import loaders

router = APIRouter(prefix="/api/samples", tags=["samples"])


@router.get("")
def get_samples():
    mock = loaders.load_mock_requests()

    text_samples = [
        {"type": "text", "id": m.get("id"), "text": m.get("text")} for m in mock
    ]

    # 从历史工单抽取样例录音：以 source_id 作为文件名，前端上传可按文件名精确转写
    audio_samples = []
    for c in loaders.load_historical_cases():
        sid = c.get("source_id", "")
        if not sid:
            continue
        audio_samples.append(
            {
                "type": "audio",
                "source_id": sid,
                "filename": f"{sid}.mp3",
                "category": c.get("category"),
                "title": c.get("title"),
                "preview": (c.get("request_content") or "")[:80],
            }
        )

    return {
        "text_samples": text_samples,
        "audio_samples": audio_samples,
        "note": "上传官方样例录音（保持原文件名 source_id.mp3）可按文件名精确转写；"
        "其他录音在未安装 ASR 引擎时返回模拟示例文本。",
    }
