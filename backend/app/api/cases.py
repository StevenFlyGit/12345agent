"""案件相关 API：创建、查询、各阶段触发、确认、处理录入。"""
from __future__ import annotations

from fastapi import APIRouter, HTTPException, Request

from app.workflow import orchestrator, store

router = APIRouter(prefix="/api/cases", tags=["cases"])


@router.post("")
async def create_case(request: Request):
    """创建案件。支持 JSON({text?, audio_filename?}) 或 multipart/form-data(audio 文件)。"""
    content_type = request.headers.get("content-type", "")
    text = None
    audio_filename = None
    audio_bytes = None

    if "multipart/form-data" in content_type:
        form = await request.form()
        text = form.get("text")
        audio = form.get("audio")
        if audio is not None:
            # audio 可能是 UploadFile 或纯字符串
            if hasattr(audio, "filename"):
                audio_filename = audio.filename
                audio_bytes = await audio.read()
            else:
                audio_filename = str(audio)
    else:
        try:
            body = await request.json()
        except Exception:
            body = {}
        text = body.get("text")
        audio_filename = body.get("audio_filename")

    if not text and not audio_filename and not audio_bytes:
        raise HTTPException(status_code=400, detail="请提供 text 或 audio")

    case = orchestrator.create_case(
        text=text, audio_filename=audio_filename, audio_bytes=audio_bytes
    )
    return case


@router.get("")
def list_cases():
    return [c.model_dump() for c in store.list()]


@router.get("/{case_id}")
def get_case(case_id: str):
    from app.workflow import store

    case = store.get(case_id)
    if case is None:
        raise HTTPException(status_code=404, detail="case_id 不存在")
    return case


@router.post("/{case_id}/workorder")
def run_workorder(case_id: str):
    try:
        return orchestrator.run_workorder(case_id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/{case_id}/classify")
def run_classify(case_id: str):
    try:
        return orchestrator.run_classify(case_id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/{case_id}/reply")
def run_reply(case_id: str):
    try:
        return orchestrator.run_reply(case_id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/{case_id}/confirm")
async def confirm_case(case_id: str, request: Request):
    try:
        body = await request.json()
    except Exception:
        body = {}
    operator = body.get("operator")
    note = body.get("note")
    if not operator:
        raise HTTPException(status_code=400, detail="operator 必填")
    try:
        return orchestrator.confirm(case_id, operator=operator, note=note)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.post("/{case_id}/handling")
async def record_handling(case_id: str, request: Request):
    try:
        body = await request.json()
    except Exception:
        body = {}
    text = body.get("text")
    if not text:
        raise HTTPException(status_code=400, detail="text 必填")
    try:
        return orchestrator.record_handling(case_id, text=text)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
