"""政策文件上传、元数据确认与 policy_docs 入库接口。"""
from __future__ import annotations

import json

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.services import policy_uploads


@pytest.fixture
def isolated_policy_uploads(tmp_path, monkeypatch):
    upload_root = tmp_path / "staging"
    policy_root = tmp_path / "policies"
    monkeypatch.setattr(policy_uploads, "UPLOAD_ROOT", upload_root)
    monkeypatch.setattr(policy_uploads, "POLICY_ROOT", policy_root)
    monkeypatch.setattr(
        policy_uploads.loaders,
        "category_name_to_code",
        lambda: {"城乡建设": "urban_construction"},
    )
    indexed = []

    def fake_add(documents):
        indexed.extend(documents)
        return len(documents)

    monkeypatch.setattr(policy_uploads, "_add_to_policy_collection", fake_add)
    return upload_root, policy_root, indexed


def test_upload_then_complete_policy_metadata(isolated_policy_uploads):
    upload_root, policy_root, indexed = isolated_policy_uploads
    client = TestClient(app)

    staged = client.post(
        "/api/policies/uploads",
        files={"file": ("物业管理办法.txt", "物业维修资金申请与使用管理规定。".encode("utf-8"), "text/plain")},
    )

    assert staged.status_code == 201
    ticket = staged.json()
    assert ticket["filename"] == "物业管理办法.txt"
    assert ticket["source_name"] == "物业管理办法"
    assert (upload_root / ticket["upload_id"] / "物业管理办法.txt").exists()

    completed = client.post(
        f"/api/policies/uploads/{ticket['upload_id']}/complete",
        json={
            "source_name": "芜湖市物业管理办法",
            "publisher": "芜湖市住房和城乡建设局",
            "category_name": "城乡建设",
        },
    )

    assert completed.status_code == 200
    assert completed.json() == {"message": "上传成功"}
    assert indexed
    assert all(doc.metadata["upload_id"] == ticket["upload_id"] for doc in indexed)
    assert not (upload_root / ticket["upload_id"]).exists()

    meta_files = list(policy_root.rglob("*.meta.json"))
    assert len(meta_files) == 1
    meta = json.loads(meta_files[0].read_text(encoding="utf-8"))
    assert meta["source_name"] == "芜湖市物业管理办法"
    assert meta["publisher"] == "芜湖市住房和城乡建设局"
    assert meta["category_name"] == "城乡建设"
    assert meta["collected_at"]
    assert meta["uploaded_at"]
    assert meta["doc_type"] == "policy"
    assert meta["sensitive_level"] == "public_demo"
    assert meta["usage_scope"] == "用于政策依据检索"


def test_policy_upload_rejects_invalid_file_and_missing_metadata(isolated_policy_uploads):
    client = TestClient(app)

    invalid = client.post(
        "/api/policies/uploads",
        files={"file": ("policy.exe", b"not allowed", "application/octet-stream")},
    )
    assert invalid.status_code == 422

    staged = client.post(
        "/api/policies/uploads",
        files={"file": ("policy.md", b"# policy", "text/markdown")},
    )
    ticket = staged.json()
    missing = client.post(
        f"/api/policies/uploads/{ticket['upload_id']}/complete",
        json={"source_name": "测试政策", "publisher": "测试单位"},
    )
    assert missing.status_code == 422

    cancelled = client.delete(f"/api/policies/uploads/{ticket['upload_id']}")
    assert cancelled.status_code == 200
    assert cancelled.json() == {"message": "已取消上传"}

def test_policy_upload_rolls_back_when_vector_write_fails(isolated_policy_uploads, monkeypatch):
    upload_root, policy_root, _ = isolated_policy_uploads
    client = TestClient(app)

    staged = client.post(
        "/api/policies/uploads",
        files={"file": ("policy.txt", "政策正文".encode("utf-8"), "text/plain")},
    )
    ticket = staged.json()

    def fail_add(_documents):
        raise RuntimeError("vector store unavailable")

    monkeypatch.setattr(policy_uploads, "_add_to_policy_collection", fail_add)
    completed = client.post(
        f"/api/policies/uploads/{ticket['upload_id']}/complete",
        json={
            "source_name": "测试政策",
            "publisher": "测试单位",
            "category_name": "城乡建设",
        },
    )

    assert completed.status_code == 422
    assert "文档写入向量库失败" in completed.json()["detail"]
    assert (upload_root / ticket["upload_id"] / "policy.txt").exists()
    assert not (policy_root / "uploads" / ticket["upload_id"]).exists()




def _complete_test_policy(client: TestClient) -> dict:
    staged = client.post(
        "/api/policies/uploads",
        files={"file": ("policy.txt", "政策正文".encode("utf-8"), "text/plain")},
    )
    ticket = staged.json()
    completed = client.post(
        f"/api/policies/uploads/{ticket['upload_id']}/complete",
        json={
            "source_name": "测试政策",
            "publisher": "测试单位",
            "category_name": "城乡建设",
        },
    )
    assert completed.status_code == 200
    return ticket


def test_list_and_delete_completed_policy(isolated_policy_uploads, monkeypatch):
    _, policy_root, _ = isolated_policy_uploads
    client = TestClient(app)
    ticket = _complete_test_policy(client)

    listed = client.get("/api/policies/files")
    assert listed.status_code == 200
    payload = listed.json()
    assert payload["total"] == 1
    assert payload["items"][0]["upload_id"] == ticket["upload_id"]
    assert payload["items"][0]["filename"] == "policy.txt"
    assert payload["items"][0]["source_name"] == "测试政策"
    assert payload["items"][0]["publisher"] == "测试单位"
    assert payload["items"][0]["category_name"] == "城乡建设"
    assert payload["items"][0]["file_size"] > 0
    assert payload["items"][0]["uploaded_at"]

    deleted_uploads = []

    def fake_delete(upload_id):
        deleted_uploads.append(upload_id)
        return 1

    monkeypatch.setattr(policy_uploads, "_delete_from_policy_collection", fake_delete)
    deleted = client.delete(f"/api/policies/files/{ticket['upload_id']}")

    assert deleted.status_code == 200
    assert deleted.json() == {"message": "政策文件已删除", "deleted_vectors": 1}
    assert deleted_uploads == [ticket["upload_id"]]
    assert not (policy_root / "uploads" / ticket["upload_id"]).exists()
    assert client.get("/api/policies/files").json()["total"] == 0


def test_policy_delete_restores_files_when_vector_delete_fails(
    isolated_policy_uploads, monkeypatch
):
    _, policy_root, _ = isolated_policy_uploads
    client = TestClient(app)
    ticket = _complete_test_policy(client)
    destination = policy_root / "uploads" / ticket["upload_id"]

    def fail_delete(_upload_id):
        raise RuntimeError("vector store unavailable")

    monkeypatch.setattr(policy_uploads, "_delete_from_policy_collection", fail_delete)
    deleted = client.delete(f"/api/policies/files/{ticket['upload_id']}")

    assert deleted.status_code == 500
    assert "向量索引删除失败" in deleted.json()["detail"]
    assert destination.is_dir()
    assert (destination / "policy.txt").is_file()
    assert client.get("/api/policies/files").json()["total"] == 1


def test_policy_file_delete_returns_not_found(isolated_policy_uploads):
    client = TestClient(app)
    response = client.delete("/api/policies/files/not-an-upload-id")
    assert response.status_code == 404
