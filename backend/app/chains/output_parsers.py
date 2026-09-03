"""LangChain 结构化输出模型与解析器。"""
from __future__ import annotations

from pydantic import BaseModel, Field


class UnderstandingPayload(BaseModel):
    """LLM 诉求理解输出，不包含系统补充字段。"""

    time: str | None = Field(default=None, description="时间")
    location: str | None = Field(default=None, description="地点")
    parties: list[str] = Field(default_factory=list, description="涉及人员或对象")
    event: str | None = Field(default=None, description="主要事件")
    demand: str | None = Field(default=None, description="群众诉求")
    other: str | None = Field(default=None, description="其他相关信息")
    needs_clarification: bool = Field(default=False, description="是否需要补充确认")
    missing_fields: list[str] = Field(default_factory=list, description="缺失字段")
    urgent: bool = Field(default=False, description="是否紧急")
    repeat_request: bool = Field(default=False, description="是否重复反映")


class ClassificationPayload(BaseModel):
    """LLM 分类输出。"""

    category_name: str | None = Field(default=None, description="12 类之一的中文名")
    confidence: float = Field(default=0.0, description="分类置信度，0 到 1")
    needs_manual: bool = Field(default=False, description="是否需要人工复核")


class WorkOrderPayload(BaseModel):
    """LLM 工单生成输出。"""

    title: str = Field(description="工单标题")
    summary: str = Field(default="", description="问题摘要")
    content: str = Field(default="", description="工单正文")
    key_elements: list[str] = Field(default_factory=list, description="关键要素")
    suggested_category: str | None = Field(default=None, description="建议类别中文名")


class ReplyPayload(BaseModel):
    """LLM 回复辅助输出。"""

    acceptance_notice: str = Field(default="", description="受理提示")
    handling_suggestion: str = Field(default="", description="办理建议")
    pre_reply: str = Field(default="", description="预回复正文")
    callback_script: str = Field(default="", description="回访话术")
    modification_tips: list[str] = Field(default_factory=list, description="修改建议")

