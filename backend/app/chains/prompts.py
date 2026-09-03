"""集中管理各业务阶段 PromptTemplate。"""
from __future__ import annotations

from langchain_core.prompts import ChatPromptTemplate

CATEGORY_NAMES = "经济财贸、卫生健康、市场监管、生态环境、公共服务、城乡建设、公共安全、劳动和社会保障、交通运输、科教文体、农林水土、城市管理"

UNDERSTAND_PROMPT = ChatPromptTemplate.from_messages(
    [
        (
            "system",
            "你是 12345 政务服务热线诉求理解助手。"
            "请从群众诉求文本中抽取结构化要素，忠实反映原文，不得虚构事实。"
            "如果信息缺失、表达不清或存在歧义，请标记 needs_clarification 并列出 missing_fields。"
            "\n{format_instructions}",
        ),
        ("human", "文本：{text}"),
    ]
)

CLASSIFY_PROMPT = ChatPromptTemplate.from_messages(
    [
        (
            "system",
            "你是 12345 热线工单分类助手。"
            "请判断群众诉求所属类别，仅能从以下 12 类中选择："
            f"{CATEGORY_NAMES}。"
            "RAG 检索上下文仅作为分类、承办单位职责和相似案例参考；"
            "如果信息不足、职责交叉或无法确定，请标记 needs_manual。"
            "\n{format_instructions}",
        ),
        (
            "human",
            "文本：{text}\n"
            "已理解结果：{understanding}\n"
            "RAG 检索上下文：{context}",
        ),
    ]
)

WORKORDER_PROMPT = ChatPromptTemplate.from_messages(
    [
        (
            "system",
            "你是 12345 热线工单生成助手。"
            "请基于群众原始诉求和结构化理解结果生成标准化工单。"
            "相似历史工单只可作为标题、摘要和要素组织方式的参考，"
            "不得复制敏感信息，不得擅自改变事实或补充未经确认的信息。"
            "\n{format_instructions}",
        ),
        (
            "human",
            "原文：{text}\n"
            "已理解结果：{understanding}\n"
            "分类结果：{classification}\n"
            "相似历史工单上下文：{context}",
        ),
    ]
)

REPLY_PROMPT = ChatPromptTemplate.from_messages(
    [
        (
            "system",
            "你是 12345 热线回复辅助助手。"
            "请基于诉求理解、分类结果、历史案例和政策依据生成受理提示、办理建议、预回复和回访话术。"
            "内容仅供工作人员参考，不得承诺未经确认的处理结果、办理时限、补偿或执法结论。"
            "如上下文不足，请提示工作人员人工确认。"
            "\n{format_instructions}",
        ),
        (
            "human",
            "理解结果：{understanding}\n"
            "分类结果：{classification}\n"
            "历史案例与政策依据上下文：{context}",
        ),
    ]
)
