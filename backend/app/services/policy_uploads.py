"""政策文件暂存、元数据落盘与 policy_docs 增量索引。"""
from __future__ import annotations

import json
import re
import shutil
from datetime import date, datetime
from pathlib import Path
from threading import Lock
from uuid import uuid4

from fastapi import UploadFile

from app.data import loaders
from app.rag.documents import document_ids
from app.rag.policy_loaders import (
    POLICY_ROOT,
    SUPPORTED_SUFFIXES,
    load_policy_documents,
    meta_path_for,
    validate_policy_sources,
)
from app.rag.vectorstore import (
    POLICY_COLLECTION,
    get_chroma_client,
    get_vectorstore,
)

UPLOAD_ROOT = Path(__file__).resolve().parents[2] / "storage" / "policy_uploads"
MAX_UPLOAD_BYTES = 20 * 1024 * 1024
DEFAULT_USAGE_SCOPE = "用于政策依据检索"
_UPLOAD_ID_PATTERN = re.compile(r"^[0-9a-f]{32}$")
_INDEX_LOCK = Lock()


class PolicyUploadError(Exception):
    """政策文件上传或入库失败。"""


class PolicyUploadNotFoundError(PolicyUploadError):
    """上传凭据不存在或已经失效。"""


class PolicyFileNotFoundError(PolicyUploadError):
    """已入库的政策文件不存在。"""


class PolicyFileDeleteError(PolicyUploadError):
    """政策文件或对应向量删除失败。"""


def _upload_dir(upload_id: str) -> Path:
    if not _UPLOAD_ID_PATTERN.fullmatch(upload_id):
        raise PolicyUploadNotFoundError("上传记录不存在或已经失效")
    return UPLOAD_ROOT / upload_id


def _safe_filename(raw_name: str | None) -> str:
    original = (raw_name or "").replace("\\", "/").split("/")[-1]
    cleaned = re.sub(r'[<>:"/\\|?*\x00-\x1f]', "_", original).strip(" .")
    if not cleaned:
        raise PolicyUploadError("文件名不能为空")
    if cleaned.lower().endswith(".meta.json"):
        raise PolicyUploadError("不能上传 .meta.json 元数据文件")
    if Path(cleaned).suffix.lower() not in SUPPORTED_SUFFIXES:
        supported = "、".join(sorted(SUPPORTED_SUFFIXES))
        raise PolicyUploadError(f"不支持该文件类型，支持：{supported}")
    return cleaned


async def stage_upload(upload: UploadFile) -> dict[str, str]:
    """保存用户刚选择的文件，成功后由前端继续收集元数据。"""
    filename = _safe_filename(upload.filename)
    upload_id = uuid4().hex
    upload_dir = _upload_dir(upload_id)
    upload_dir.mkdir(parents=True, exist_ok=False)
    target = upload_dir / filename
    written = 0
    try:
        with target.open("xb") as destination:
            while chunk := await upload.read(1024 * 1024):
                written += len(chunk)
                if written > MAX_UPLOAD_BYTES:
                    raise PolicyUploadError("文件大小不能超过 20 MB")
                destination.write(chunk)
        if written == 0:
            raise PolicyUploadError("不能上传空文件")
    except Exception:
        shutil.rmtree(upload_dir, ignore_errors=True)
        raise
    finally:
        await upload.close()

    return {
        "upload_id": upload_id,
        "filename": filename,
        "source_name": Path(filename).stem,
    }


def _staged_file(upload_id: str) -> Path:
    upload_dir = _upload_dir(upload_id)
    if not upload_dir.is_dir():
        raise PolicyUploadNotFoundError("上传记录不存在或已经失效")
    files = [path for path in upload_dir.iterdir() if path.is_file()]
    if len(files) != 1:
        raise PolicyUploadNotFoundError("上传文件不存在或状态异常")
    return files[0]


def _add_to_policy_collection(documents) -> int:
    """增量写入单次上传的文档；失败时清理本次生成的向量。"""
    store = get_vectorstore(POLICY_COLLECTION)
    ids = document_ids(POLICY_COLLECTION, documents)
    try:
        for start in range(0, len(documents), 64):
            end = start + 64
            store.add_documents(documents[start:end], ids=ids[start:end])
    except Exception:
        try:
            store.delete(ids=ids)
        except Exception:
            pass
        raise
    return len(documents)


def complete_upload(upload_id: str, metadata: dict[str, str]) -> dict[str, str]:
    """保存政策元数据，并将当前文件增量写入 policy_docs。"""
    staged_file = _staged_file(upload_id)
    category_name = metadata["category_name"].strip()
    valid_categories = set(loaders.category_name_to_code())
    if category_name not in valid_categories:
        raise PolicyUploadError("所属分类必须选择现有工单分类")

    destination_dir = POLICY_ROOT / "uploads" / upload_id
    if destination_dir.exists():
        raise PolicyUploadError("该上传记录已经处理")
    meta = {
        "source_name": metadata["source_name"].strip(),
        "publisher": metadata["publisher"].strip(),
        "category_name": category_name,
        "collected_at": date.today().isoformat(),
        "uploaded_at": datetime.now().astimezone().isoformat(timespec="seconds"),
        "doc_type": "policy",
        "sensitive_level": "public_demo",
        "usage_scope": DEFAULT_USAGE_SCOPE,
        "version": "manual",
    }
    destination_file = destination_dir / staged_file.name
    meta_path = meta_path_for(destination_file)

    try:
        destination_dir.mkdir(parents=True, exist_ok=False)
        shutil.move(str(staged_file), str(destination_file))
        meta_path.write_text(
            json.dumps(meta, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        issues = [
            issue
            for issue in validate_policy_sources(destination_dir)
            if issue.level == "error"
        ]
        if issues:
            raise PolicyUploadError(issues[0].message)

        documents = load_policy_documents(destination_dir)
        if not documents:
            raise PolicyUploadError("文件中没有可写入向量库的文本内容")
        for document in documents:
            document.metadata["upload_id"] = upload_id

        with _INDEX_LOCK:
            _add_to_policy_collection(documents)
    except PolicyUploadError:
        if destination_file.exists():
            _upload_dir(upload_id).mkdir(parents=True, exist_ok=True)
            shutil.move(str(destination_file), str(_upload_dir(upload_id) / staged_file.name))
        shutil.rmtree(destination_dir, ignore_errors=True)
        raise
    except Exception as exc:
        if destination_file.exists():
            _upload_dir(upload_id).mkdir(parents=True, exist_ok=True)
            shutil.move(str(destination_file), str(_upload_dir(upload_id) / staged_file.name))
        shutil.rmtree(destination_dir, ignore_errors=True)
        raise PolicyUploadError(f"文档写入向量库失败：{exc}") from exc

    shutil.rmtree(_upload_dir(upload_id), ignore_errors=True)
    return {"message": "上传成功"}


def discard_upload(upload_id: str) -> None:
    """用户取消补充元数据时删除暂存文件。"""
    upload_dir = _upload_dir(upload_id)
    if upload_dir.exists():
        shutil.rmtree(upload_dir, ignore_errors=True)



def _completed_upload_dir(upload_id: str) -> Path:
    if not _UPLOAD_ID_PATTERN.fullmatch(upload_id):
        raise PolicyFileNotFoundError("政策文件不存在或已经删除")
    return POLICY_ROOT / "uploads" / upload_id


def _policy_file_item(upload_dir: Path) -> dict[str, str | int] | None:
    source_files = [
        path
        for path in upload_dir.iterdir()
        if path.is_file() and not path.name.endswith(".meta.json")
    ]
    if len(source_files) != 1:
        return None
    source_file = source_files[0]
    meta_path = meta_path_for(source_file)
    if not meta_path.is_file():
        return None
    try:
        metadata = json.loads(meta_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None

    uploaded_at = str(metadata.get("uploaded_at") or "").strip()
    if not uploaded_at:
        uploaded_at = datetime.fromtimestamp(
            meta_path.stat().st_mtime
        ).astimezone().isoformat(timespec="seconds")

    return {
        "upload_id": upload_dir.name,
        "filename": source_file.name,
        "source_name": str(metadata.get("source_name") or source_file.stem),
        "publisher": str(metadata.get("publisher") or ""),
        "category_name": str(metadata.get("category_name") or ""),
        "uploaded_at": uploaded_at,
        "file_size": source_file.stat().st_size,
    }


def list_policy_files(page: int = 1, page_size: int = 20) -> dict:
    """列出用户已完成入库的政策文件，不读取文件正文。"""
    uploads_root = POLICY_ROOT / "uploads"
    items: list[dict[str, str | int]] = []
    if uploads_root.is_dir():
        for upload_dir in uploads_root.iterdir():
            if not upload_dir.is_dir() or not _UPLOAD_ID_PATTERN.fullmatch(upload_dir.name):
                continue
            item = _policy_file_item(upload_dir)
            if item is not None:
                items.append(item)

    items.sort(key=lambda item: str(item["uploaded_at"]), reverse=True)
    total = len(items)
    start = (page - 1) * page_size
    return {
        "items": items[start : start + page_size],
        "total": total,
        "page": page,
        "page_size": page_size,
    }


def _delete_from_policy_collection(upload_id: str) -> int:
    """按上传编号删除对应的全部政策向量。"""
    client = get_chroma_client()
    try:
        collection = client.get_collection(POLICY_COLLECTION)
    except Exception:
        return 0
    records = collection.get(where={"upload_id": upload_id})
    ids = records.get("ids") or []
    if ids:
        collection.delete(ids=ids)
    return len(ids)


def delete_policy_file(upload_id: str) -> dict[str, str | int]:
    """删除用户上传的政策源文件、元数据和相应向量。"""
    destination_dir = _completed_upload_dir(upload_id)
    if not destination_dir.is_dir():
        raise PolicyFileNotFoundError("政策文件不存在或已经删除")

    trash_root = UPLOAD_ROOT.parent / "policy_delete_trash"
    trash_dir = trash_root / upload_id
    with _INDEX_LOCK:
        trash_root.mkdir(parents=True, exist_ok=True)
        if trash_dir.exists():
            raise PolicyFileDeleteError("该政策文件正在删除，请稍后重试")
        destination_dir.rename(trash_dir)
        try:
            deleted_vectors = _delete_from_policy_collection(upload_id)
        except Exception as exc:
            trash_dir.rename(destination_dir)
            raise PolicyFileDeleteError(f"向量索引删除失败：{exc}") from exc

        try:
            shutil.rmtree(trash_dir)
        except Exception as exc:
            if trash_dir.exists() and not destination_dir.exists():
                trash_dir.rename(destination_dir)
            raise PolicyFileDeleteError(f"政策文件删除失败：{exc}") from exc

    try:
        trash_root.rmdir()
    except OSError:
        pass
    return {"message": "政策文件已删除", "deleted_vectors": deleted_vectors}
