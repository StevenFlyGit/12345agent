"""回复辅助 LangChain Runnable。"""
from __future__ import annotations

from langchain_core.output_parsers import PydanticOutputParser

from app.chains.fallbacks import try_invoke
from app.chains.models import get_chat_model
from app.chains.output_parsers import ReplyPayload
from app.chains.prompts import REPLY_PROMPT
from app.schemas.models import ClassificationResult, UnderstandingResult


def invoke_reply_chain(
    understanding: UnderstandingResult,
    classification: ClassificationResult | None = None,
    context: str = "无",
) -> ReplyPayload | None:
    """调用回复辅助 chain；失败时返回 None。"""
    model = get_chat_model()
    if model is None:
        return None

    parser = PydanticOutputParser(pydantic_object=ReplyPayload)
    chain = (
        REPLY_PROMPT.partial(format_instructions=parser.get_format_instructions())
        | model
        | parser
    )
    return try_invoke(
        lambda: chain.invoke(
            {
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
