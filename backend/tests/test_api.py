"""API 闭环冒烟测试（本地确定性引擎，无需 LLM Key）。

运行：.conda/Scripts/python.exe -m pytest tests/test_api.py -q
"""
from __future__ import annotations

from fastapi.testclient import TestClient

from app.main import app

TEXT = "南陵县某理发店没有公示服务价格，也没有在醒目位置悬挂营业执照，希望有关部门核查。"


def test_health():
    c = TestClient(app)
    assert c.get("/health").json()["status"] == "ok"


def test_full_loop():
    c = TestClient(app)
    # 1) 创建案件
    r = c.post("/api/cases", json={"text": TEXT})
    assert r.status_code == 200
    case = r.json()
    case_id = case["case_id"]
    assert case["understanding"]["source"] == "local-engine"

    # 2) 工单
    wo = c.post(f"/api/cases/{case_id}/workorder").json()
    assert wo["suggested_category"] == "市场监管"

    # 3) 分类
    cls = c.post(f"/api/cases/{case_id}/classify").json()
    assert cls["category_name"] == "市场监管"
    assert cls["suggestions"][0]["main"]

    # 4) 回复
    rp = c.post(f"/api/cases/{case_id}/reply").json()
    assert rp["pre_reply"]

    # 5) 确认
    cf = c.post(f"/api/cases/{case_id}/confirm", json={"operator": "tester"}).json()
    assert cf["confirmed"] is True
    assert cf["audit_log"][-1]["operator"] == "tester"

    # 6) 详情可回看
    full = c.get(f"/api/cases/{case_id}").json()
    assert full["work_order"] and full["classification"] and full["reply"]


def test_samples_and_history():
    c = TestClient(app)
    s = c.get("/api/samples").json()
    assert len(s["text_samples"]) == 8
    h = c.get("/api/history", params={"q": "理发店收费"}).json()
    assert "results" in h


def test_audio_sample_match():
    c = TestClient(app)
    r = c.post("/api/cases", json={"audio_filename": "260715111208005.mp3"})
    assert r.status_code == 200
    assert r.json()["understanding"]["transcript_source"] == "sample-match"
