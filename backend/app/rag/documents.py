"""将项目结构化数据转换为 LangChain Document。"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Iterable

from langchain_core.documents import Document

from app.data import loaders


def _safe_metadata(data: dict) -> dict:
    """Chroma metadata 只保留标量；复杂值转 JSON 字符串。"""
    safe: dict = {}
    for key, value in data.items():
        if value is None:
            safe[key] = ""
        elif isinstance(value, (str, int, float, bool)):
            safe[key] = value
        else:
            safe[key] = json.dumps(value, ensure_ascii=False)
    return safe


def _doc(
    content: str,
    *,
    doc_type: str,
    source_name: str,
    source_file: str = "",
    **metadata,
) -> Document:
    return Document(
        page_content=content.strip(),
        metadata=_safe_metadata(
            {
                "doc_type": doc_type,
                "source_name": source_name,
                "source_file": source_file,
                "sensitive_level": "public_demo",
                **metadata,
            }
        ),
    )


def build_category_documents() -> list[Document]:
    """分类目录 -> Document。"""
    catalog = loaders.load_category_catalog()
    docs: list[Document] = []
    for item in catalog.get("categories", []):
        code = item.get("code", "")
        name = item.get("name", "")
        content = f"事项类别：{name}\n类别编码：{code}\n说明：12345 热线事项一级分类候选。"
        docs.append(
            _doc(
                content,
                doc_type="category",
                source_name=catalog.get("source", "事项分类目录"),
                source_file="category_catalog.json",
                category_code=code,
                category_name=name,
                version=catalog.get("schema_version", "1.0"),
            )
        )
    return docs


def build_department_rule_documents() -> list[Document]:
    """部门职责规则 -> Document。"""
    rules_doc = loaders.load_department_rules()
    docs: list[Document] = []
    for rule in rules_doc.get("rules", []):
        keywords = rule.get("keywords", []) or []
        co_departments = rule.get("co_departments", []) or []
        content = "\n".join(
            [
                f"事项类别：{rule.get('category_name', '')}",
                f"主责部门：{rule.get('department', '')}",
                f"协办部门：{'、'.join(co_departments)}",
                f"职责说明：{rule.get('responsibilities', '')}",
                f"关键词：{'、'.join(keywords)}",
                f"备注：{rule.get('note', '')}",
            ]
        )
        docs.append(
            _doc(
                content,
                doc_type="department_rule",
                source_name=rule.get("source_name", "部门职责规则"),
                source_file="department_rules.json",
                category_code=rule.get("category_code", ""),
                category_name=rule.get("category_name", ""),
                department=rule.get("department", ""),
                co_departments=co_departments,
                keywords=keywords,
                version=rule.get("version", rules_doc.get("schema_version", "1.0")),
            )
        )
    return docs


def build_historical_case_documents() -> list[Document]:
    """历史工单样例 -> Document。"""
    docs: list[Document] = []
    for item in loaders.load_historical_cases():
        departments = item.get("handling_departments", []) or []
        content = "\n".join(
            [
                f"历史工单编号：{item.get('source_id', '')}",
                f"事项类别：{item.get('category', '')}",
                f"标题：{item.get('title', '')}",
                f"群众诉求：{item.get('request_content', '')}",
                f"办理单位：{'、'.join(departments)}",
                f"答复内容：{item.get('reply_content', '')}",
                f"区域：{item.get('region', '')}",
            ]
        )
        docs.append(
            _doc(
                content,
                doc_type="historical_case",
                source_name="赛事官方样例工单",
                source_file=item.get("source_file", "work_orders.json"),
                source_id=item.get("source_id", ""),
                accepted_at=item.get("accepted_at", ""),
                category_name=item.get("category", ""),
                title=item.get("title", ""),
                handling_departments=departments,
                region=item.get("region", ""),
                urgent=bool(item.get("urgent", False)),
                repeat_request=bool(item.get("repeat_request", False)),
            )
        )
    return docs


def build_official_documents() -> dict[str, list[Document]]:
    """返回官方数据对应的 collection -> Document 列表。"""
    return {
        "category_catalog": build_category_documents(),
        "department_rules": build_department_rule_documents(),
        "historical_cases": build_historical_case_documents(),
    }


def document_id(collection_name: str, document: Document) -> str:
    """生成稳定文档 ID，便于重复构建索引。"""
    basis = json.dumps(
        {
            "collection": collection_name,
            "content": document.page_content,
            "metadata": document.metadata,
        },
        ensure_ascii=False,
        sort_keys=True,
    )
    digest = hashlib.sha1(basis.encode("utf-8")).hexdigest()
    return f"{collection_name}_{digest}"


def document_ids(collection_name: str, documents: Iterable[Document]) -> list[str]:
    return [document_id(collection_name, doc) for doc in documents]

