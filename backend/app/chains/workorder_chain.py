"""工单生成 LangChain Runnable。"""
from __future__ import annotations

from langchain_core.output_parsers import PydanticOutputParser

from app.chains.fallbacks import try_invoke
from app.chains.models import get_chat_model
from app.chains.output_parsers import WorkOrderPayload
from app.chains.prompts import WORKORDER_PROMPT
from app.schemas.models import ClassificationResult, UnderstandingResult


def invoke_workorder_chain(
    text: str,
    understanding: UnderstandingResult,
    classification: ClassificationResult | None = None,
    context: str = "无",
) -> WorkOrderPayload | None:
    """调用工单生成 chain；失败时返回 None。"""
    model = get_chat_model()
    if model is None:
        return None

    parser = PydanticOutputParser(pydantic_object=WorkOrderPayload)
    chain = (
        WORKORDER_PROMPT.partial(
            format_instructions=parser.get_format_instructions()
        )
        | model
        | parser
    )
    return try_invoke(
        lambda: chain.invoke(
            {
                "text": text,
                "understanding": understanding.model_dump_json(),
                "classification": (
                    classification.model_dump_json()
                    if classification is not None
                    else "无"
                ),
                "context": context,
            }
        )
    )
