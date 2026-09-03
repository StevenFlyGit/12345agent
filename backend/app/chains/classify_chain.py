"""事项分类 LangChain Runnable。"""
from __future__ import annotations

from langchain_core.output_parsers import PydanticOutputParser

from app.chains.fallbacks import try_invoke
from app.chains.models import get_chat_model
from app.chains.output_parsers import ClassificationPayload
from app.chains.prompts import CLASSIFY_PROMPT
from app.schemas.models import UnderstandingResult


def invoke_classify_chain(
    text: str,
    understanding: UnderstandingResult | None = None,
    context: str = "无",
) -> ClassificationPayload | None:
    """调用分类 chain；失败时返回 None。"""
    model = get_chat_model()
    if model is None:
        return None

    parser = PydanticOutputParser(pydantic_object=ClassificationPayload)
    chain = (
        CLASSIFY_PROMPT.partial(format_instructions=parser.get_format_instructions())
        | model
        | parser
    )
    return try_invoke(
        lambda: chain.invoke(
            {
                "text": text,
                "understanding": (
                    understanding.model_dump_json()
                    if understanding is not None
                    else "无"
                ),
                "context": context,
            }
        )
    )
