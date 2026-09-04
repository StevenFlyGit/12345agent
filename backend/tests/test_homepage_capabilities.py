"""首页配套能力：部门规则管理与 SPA 路由回退。"""
from __future__ import annotations

import json

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.services import department_rules


@pytest.fixture
def isolated_rules(tmp_path, monkeypatch):
    path = tmp_path / "department_rules.json"
    document = {
        "schema_version": "1.0",
        "notice": "测试规则",
        "rule_fields": [
            "category_code",
            "category_name",
            "department",
            "co_departments",
            "keywords",
            "responsibilities",
            "source_name",
            "version",
            "note",
        ],
        "rules": [
            {
                "category_code": "market_regulation",
                "category_name": "市场监管",
                "department": "市场监管局",
                "co_departments": ["属地政府"],
                "keywords": ["价格", "食品"],
                "responsibilities": "负责市场监管领域诉求。",
                "source_name": "测试来源",
                "version": "demo-0.1",
                "note": "保留字段",
            },
            {
                "category_code": "health",
                "category_name": "卫生健康",
                "department": "卫健委",
                "co_departments": [],
                "keywords": ["医院"],
                "responsibilities": "负责卫生健康领域诉求。",
                "source_name": "测试来源",
                "version": "demo-0.1",
                "note": "保留字段",
            },
        ],
    }
    path.write_text(
        json.dumps(document, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    monkeypatch.setattr(department_rules, "RULES_PATH", path)

    def fake_sync():
        return len(json.loads(path.read_text(encoding="utf-8"))["rules"])

    monkeypatch.setattr(department_rules, "_sync_index", fake_sync)
    return path


def test_rules_get_update_delete(isolated_rules):
    client = TestClient(app)

    listed = client.get("/api/departments/rules")
    assert listed.status_code == 200
    assert listed.json()["filename"] == "department_rules.json"
    assert len(listed.json()["rules"]) == 2

    changed = client.put(
        "/api/departments/rules/market_regulation",
        json={
            "category_name": "市场监管（更新）",
            "department": "市场监督管理局",
            "co_departments": ["属地政府", "属地政府", "商务局"],
            "keywords": ["价格", "计量"],
            "responsibilities": "更新后的职责说明。",
        },
    )
    assert changed.status_code == 200
    body = changed.json()
    assert body["index_count"] == 2
    assert body["rule"]["co_departments"] == ["属地政府", "商务局"]

    persisted = json.loads(isolated_rules.read_text(encoding="utf-8"))
    saved = persisted["rules"][0]
    assert saved["category_name"] == "市场监管（更新）"
    assert saved["source_name"] == "测试来源"
    assert saved["version"] == "demo-0.1"
    assert saved["note"] == "保留字段"

    deleted = client.delete("/api/departments/rules/health")
    assert deleted.status_code == 200
    assert deleted.json()["rules_count"] == 1
    assert deleted.json()["index_count"] == 1

    missing = client.delete("/api/departments/rules/not-found")
    assert missing.status_code == 404


def test_rule_update_rolls_back_when_index_sync_fails(
    isolated_rules, monkeypatch
):
    original = isolated_rules.read_text(encoding="utf-8")

    def fail_sync():
        raise RuntimeError("index unavailable")

    monkeypatch.setattr(department_rules, "_sync_index", fail_sync)

    with pytest.raises(department_rules.RuleSyncError):
        department_rules.update_rule(
            "market_regulation",
            {
                "category_name": "不应保存",
                "department": "市场监管局",
                "co_departments": [],
                "keywords": [],
                "responsibilities": "不应保存",
            },
        )

    restored = json.loads(isolated_rules.read_text(encoding="utf-8"))
    expected = json.loads(original)
    assert restored == expected


def test_spa_routes_and_unknown_api():
    client = TestClient(app)
    for path in ("/", "/pipeline", "/data"):
        response = client.get(path)
        assert response.status_code == 200
        assert "text/html" in response.headers["content-type"]

    response = client.get("/api/does-not-exist")
    assert response.status_code == 404
    assert response.json()["detail"] == "API 路径不存在"
