"""外部政策文件上传与 policy_docs 入库 API。"""
from __future__ import annotations

from fastapi import APIRouter, File, HTTPException, Query, UploadFile, status
from pydantic import BaseModel, Field, field_validator

from app.services import policy_uploads

router = APIRouter(prefix="/api/policies", tags=["policies"])


class PolicyMetadataInput(BaseModel):
    source_name: str = Field(min_length=1, max_length=200)
    publisher: str = Field(min_length=1, max_length=200)
    category_name: str = Field(min_length=1, max_length=100)

    @field_validator("source_name", "publisher", "category_name")
    @classmethod
    def strip_required_text(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("必填信息不能为空")
        return cleaned


@router.get("/files")
def get_policy_files(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
):
    return policy_uploads.list_policy_files(page=page, page_size=page_size)


@router.delete("/files/{upload_id}")
def delete_policy_file(upload_id: str):
    try:
        return policy_uploads.delete_policy_file(upload_id)
    except policy_uploads.PolicyFileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except policy_uploads.PolicyFileDeleteError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.post("/uploads", status_code=status.HTTP_201_CREATED)
async def upload_policy_file(file: UploadFile = File(...)):
    try:
        return await policy_uploads.stage_upload(file)
    except policy_uploads.PolicyUploadError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.post("/uploads/{upload_id}/complete")
def complete_policy_upload(upload_id: str, metadata: PolicyMetadataInput):
    try:
        return policy_uploads.complete_upload(upload_id, metadata.model_dump())
    except policy_uploads.PolicyUploadNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except policy_uploads.PolicyUploadError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.delete("/uploads/{upload_id}")
def cancel_policy_upload(upload_id: str):
    try:
        policy_uploads.discard_upload(upload_id)
        return {"message": "已取消上传"}
    except policy_uploads.PolicyUploadNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
