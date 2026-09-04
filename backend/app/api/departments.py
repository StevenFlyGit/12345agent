"""部门规则数据管理 API。"""
from __future__ import annotations

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field, field_validator, model_validator

from app.services import department_rules

router = APIRouter(prefix="/api/departments", tags=["departments"])


class DepartmentRuleUpdate(BaseModel):
    category_name: str = Field(min_length=1)
    department: str = Field(min_length=1)
    co_departments: list[str] = Field(default_factory=list)
    keywords: list[str] = Field(default_factory=list)
    responsibilities: str = Field(min_length=1)

    @field_validator("co_departments", "keywords")
    @classmethod
    def normalize_list(cls, value: list[str]) -> list[str]:
        return list(dict.fromkeys(item.strip() for item in value if item.strip()))

    @model_validator(mode="after")
    def reject_blank_required_fields(self):
        for field in ("category_name", "department", "responsibilities"):
            if not getattr(self, field).strip():
                raise ValueError(f"{field} 不能为空")
        return self


@router.get("/rules")
def list_rules():
    try:
        return department_rules.get_document()
    except department_rules.RuleSyncError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.put("/rules/{category_code}")
def update_rule(category_code: str, update: DepartmentRuleUpdate):
    try:
        return department_rules.update_rule(
            category_code,
            update.model_dump(),
        )
    except department_rules.RuleNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except department_rules.RuleSyncError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.delete("/rules/{category_code}")
def delete_rule(category_code: str):
    try:
        return department_rules.delete_rule(category_code)
    except department_rules.RuleNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except department_rules.RuleSyncError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
