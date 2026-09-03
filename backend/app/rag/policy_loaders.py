"""自采政府公开文件加载入口。"""
from __future__ import annotations

import json
from pathlib import Path

from langchain_core.documents import Document

from app.rag.documents import _safe_metadata, document_id
from app.rag.schemas import PolicySourceMeta, PolicyValidationIssue
from app.rag.splitter import split_documents
from app.rag.vectorstore import POLICY_COLLECTION

ROOT = Path(__file__).resolve().parents[2]
POLICY_ROOT = ROOT / "data" / "raw" / "public_policies"
SUPPORTED_SUFFIXES = {".txt", ".md", ".html", ".htm", ".json", ".pdf", ".docx"}
REQUIRED_META_FIELDS = ["source_name", "source_url", "publisher", "collected_at", "usage_scope"]


def meta_path_for(file_path: Path) -> Path:
    """自采文件 foo.pdf 对应 foo.meta.json。"""
    return file_path.with_suffix(".meta.json")


def _is_policy_candidate(file_path: Path) -> bool:
    return (
        file_path.is_file()
        and not file_path.name.endswith(".meta.json")
        and file_path.name.lower() != "readme.md"
    )


def _build_loader(file_path: Path):
    """按文件类型创建 LangChain 官方/社区 DocumentLoader。"""
    suffix = file_path.suffix.lower()
    if suffix in {".txt", ".md", ".json"}:
        from langchain_community.document_loaders import TextLoader

        return TextLoader(str(file_path), encoding="utf-8", autodetect_encoding=True)
    if suffix == ".pdf":
        from langchain_community.document_loaders import PyPDFLoader

        return PyPDFLoader(str(file_path))
    if suffix == ".docx":
        from langchain_community.document_loaders import Docx2txtLoader

        return Docx2txtLoader(str(file_path))
    if suffix in {".html", ".htm"}:
        from langchain_community.document_loaders import BSHTMLLoader

        return BSHTMLLoader(str(file_path), open_encoding="utf-8")
    raise ValueError(f"暂不支持的文件类型：{file_path.suffix}")


def validate_policy_sources(root: Path | None = None) -> list[PolicyValidationIssue]:
    """校验自采政府文件是否具备配套元数据。"""
    base = root or POLICY_ROOT
    issues: list[PolicyValidationIssue] = []
    if not base.exists():
        return issues

    for file_path in sorted(base.rglob("*")):
        if not _is_policy_candidate(file_path):
            continue
        if file_path.suffix.lower() not in SUPPORTED_SUFFIXES:
            issues.append(
                PolicyValidationIssue(
                    file=str(file_path),
                    level="warning",
                    message=f"暂不支持的文件类型：{file_path.suffix}",
                )
            )
            continue

        meta_path = meta_path_for(file_path)
        if not meta_path.exists():
            issues.append(
                PolicyValidationIssue(
                    file=str(file_path),
                    message="缺少同名 .meta.json 元数据文件",
                )
            )
            continue

        try:
            meta_data = json.loads(meta_path.read_text(encoding="utf-8"))
        except Exception as exc:
            issues.append(
                PolicyValidationIssue(
                    file=str(meta_path),
                    message=f"元数据 JSON 无法解析：{exc}",
                )
            )
            continue

        for field in REQUIRED_META_FIELDS:
            if not meta_data.get(field):
                issues.append(
                    PolicyValidationIssue(
                        file=str(meta_path),
                        message=f"元数据缺少必填字段：{field}",
                    )
                )
    return issues


def load_raw_policy_documents(root: Path | None = None) -> list[Document]:
    """使用 LangChain DocumentLoader 读取自采政府文件，尚不分片。"""
    base = root or POLICY_ROOT
    if not base.exists():
        return []

    documents: list[Document] = []
    for file_path in sorted(base.rglob("*")):
        if not _is_policy_candidate(file_path):
            continue
        if file_path.suffix.lower() not in SUPPORTED_SUFFIXES:
            continue

        meta_path = meta_path_for(file_path)
        if not meta_path.exists():
            continue
        try:
            meta = PolicySourceMeta.model_validate_json(meta_path.read_text(encoding="utf-8"))
            loaded_docs = _build_loader(file_path).load()
        except Exception:
            continue

        for loaded_index, loaded in enumerate(loaded_docs):
            original_metadata = {
                **meta.model_dump(),
                "source_file": file_path.name,
                "relative_path": str(file_path.relative_to(base)),
                "loader": _build_loader(file_path).__class__.__name__,
                "loaded_doc_index": loaded_index,
                "is_chunk": False,
            }
            original_doc = Document(
                page_content=loaded.page_content,
                metadata=_safe_metadata(original_metadata),
            )
            original_doc.metadata["original_doc_id"] = document_id(
                POLICY_COLLECTION,
                original_doc,
            )
            documents.append(original_doc)
    return documents


def load_policy_documents(root: Path | None = None) -> list[Document]:
    """读取自采政府文件，经过 RecursiveCharacterTextSplitter 后生成 chunk Document。"""
    raw_documents = load_raw_policy_documents(root)
    return split_documents(raw_documents, collection_name=POLICY_COLLECTION)
