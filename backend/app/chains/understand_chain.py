"""诉求理解 LangChain Runnable。"""
from __future__ import annotations

from langchain_core.output_parsers import PydanticOutputParser

from app.chains.fallbacks import try_invoke
from app.chains.models import get_chat_model
from app.chains.output_parsers import UnderstandingPayload
from app.chains.prompts import UNDERSTAND_PROMPT


def invoke_understand_chain(text: str) -> UnderstandingPayload | None:
    """调用诉求理解 chain；失败时返回 None。"""
    model = get_chat_model()
    if model is None:
        return None

    parser = PydanticOutputParser(pydantic_object=UnderstandingPayload)
    chain = (
        UNDERSTAND_PROMPT.partial(
            format_instructions=parser.get_format_instructions() # 输出格式说明
        )
        | model
        | parser
    )
    return try_invoke(lambda: chain.invoke({"text": text}))

