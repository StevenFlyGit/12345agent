"""全部核心 Pydantic 数据模型。

对应架构文档第 3 节。所有 AI 产出模型均含 `source` 字段（"llm" | "local-engine"），
便于前端透明展示与合规审计。
"""
from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, Field


class CaseInput(BaseModel):
    """群众诉求录入：文本或录音文件名。"""

    text: Optional[str] = None
    audio_filename: Optional[str] = None


class UnderstandingResult(BaseModel):
    """诉求理解结果：结构化要素抽取。"""

    transcript: str
    transcript_source: str = Field(
        description="text | sample-match | whisper | simulated"
    )
    time: Optional[str] = None
    location: Optional[str] = None
    parties: list[str] = Field(default_factory=list)
    event: Optional[str] = None
    demand: Optional[str] = None
    other: Optional[str] = None
    needs_clarification: bool = False
    missing_fields: list[str] = Field(default_factory=list)
    urgent: bool = False
    repeat_request: bool = False
    source: str


class WorkOrder(BaseModel):
    """工单生成结果。"""

    title: str
    summary: str
    content: str
    key_elements: list[str] = Field(default_factory=list)
    suggested_category: Optional[str] = None
    source: str


class DepartmentSuggestion(BaseModel):
    """单条承办单位推荐（主责 + 协办 + 理由）。"""

    main: str
    co: list[str] = Field(default_factory=list)
    reason: str


class ClassificationResult(BaseModel):
    """分类与承办单位推荐结果。"""

    category: Optional[str] = None
    category_name: Optional[str] = None
    confidence: float = 0.0
    suggestions: list[DepartmentSuggestion] = Field(default_factory=list)
    needs_manual: bool = False
    manual_hint: Optional[str] = None
    source: str


class ReplyResult(BaseModel):
    """回复辅助结果。"""

    acceptance_notice: str
    handling_suggestion: str
    pre_reply: str
    callback_script: str
    modification_tips: list[str] = Field(default_factory=list)
    source: str


class CaseState(BaseModel):
    """贯穿全流程的案件状态，以 case_id 串联。"""

    case_id: str
    created_at: str
    input: CaseInput
    understanding: Optional[UnderstandingResult] = None
    work_order: Optional[WorkOrder] = None
    classification: Optional[ClassificationResult] = None
    reply: Optional[ReplyResult] = None
    confirmed: bool = False
    audit_log: list[dict] = Field(default_factory=list)


class HistoricalCase(BaseModel):
    """历史工单样例（来自 work_orders.json）。"""

    source_id: str
    category: Optional[str] = None
    title: Optional[str] = None
    request_content: Optional[str] = None
    handling_departments: list[str] = Field(default_factory=list)
    reply_content: Optional[str] = None
    region: Optional[str] = None
    accepted_at: Optional[str] = None
    urgent: Optional[bool] = None
    repeat_request: Optional[bool] = None
