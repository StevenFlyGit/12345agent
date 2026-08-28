"""边缘用例与智能路由验证。

运行（注意：必须加 PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 规避本机残留 hypothesis 插件崩溃）：
  cd E:\\SocialDocument\\2026-csj-Algorithm-Competition-wh\\12345Agent
  PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 .conda\\python.exe -m pytest tests\\test_edge_cases.py -v

覆盖：澄清提示、紧急识别、重复反映、分类准确性抽样、未知录音模拟转写、
审核确认审计、历史检索。接口均通过 FastAPI TestClient 从 app.main 导入 app。
"""
from __future__ import annotations

from fastapi.testclient import TestClient

from app.main import app


def _client() -> TestClient:
    return TestClient(app)


# ---------------------------------------------------------------------------
# a. 澄清提示：仅有泛化地点（"小区"），缺具体位置/小区名 -> 需澄清
# ---------------------------------------------------------------------------
def test_clarification_needed():
    c = _client()
    r = c.post(
        "/api/cases",
        json={"text": "小区门口垃圾多日无人清理，请尽快处理。"},
    )
    assert r.status_code == 200
    u = r.json()["understanding"]
    assert u["needs_clarification"] is True
    assert isinstance(u["missing_fields"], list) and len(u["missing_fields"]) > 0


# ---------------------------------------------------------------------------
# b. 紧急识别：燃气泄漏 -> urgent
# ---------------------------------------------------------------------------
def test_urgent_detection():
    c = _client()
    r = c.post(
        "/api/cases",
        json={
            "text": "现在闻到楼道内有很重的燃气味，疑似发生泄漏，请立即处理。"
        },
    )
    assert r.status_code == 200
    assert r.json()["understanding"]["urgent"] is True


# ---------------------------------------------------------------------------
# c. 重复反映：含"再次"+此前已反映 -> repeat_request
# ---------------------------------------------------------------------------
def test_repeat_request():
    c = _client()
    r = c.post(
        "/api/cases",
        json={
            "text": "我上周已经反映公司拖欠工资的问题，至今没有收到处理反馈，希望再次核实。"
        },
    )
    assert r.status_code == 200
    assert r.json()["understanding"]["repeat_request"] is True


# ---------------------------------------------------------------------------
# d. 分类准确性抽样
# ---------------------------------------------------------------------------
def test_classify_mock001_market_regulation():
    c = _client()
    r = c.post(
        "/api/cases",
        json={
            "text": "南陵县某理发店没有公示服务价格，也没有在醒目位置悬挂营业执照，希望有关部门核查。"
        },
    )
    assert r.status_code == 200
    cid = r.json()["case_id"]
    cls = c.post(f"/api/cases/{cid}/classify").json()
    assert cls["category_name"] == "市场监管"


def test_classify_mock004_transportation():
    c = _client()
    r = c.post(
        "/api/cases",
        json={"text": "市区一处公交站被社会车辆长期占用，公交车无法正常进站。"},
    )
    assert r.status_code == 200
    cid = r.json()["case_id"]
    cls = c.post(f"/api/cases/{cid}/classify").json()
    assert cls["category_name"] == "交通运输"


def test_classify_mock007_health():
    c = _client()
    r = c.post(
        "/api/cases",
        json={"text": "在医院线上预约后仍被重复收取挂号费，希望核查并退还。"},
    )
    assert r.status_code == 200
    cid = r.json()["case_id"]
    cls = c.post(f"/api/cases/{cid}/classify").json()
    assert cls["category_name"] == "卫生健康"


# ---------------------------------------------------------------------------
# e. 未知录音 -> 模拟转写（transcript_source == "simulated"）
# ---------------------------------------------------------------------------
def test_unknown_audio_simulated():
    c = _client()
    r = c.post(
        "/api/cases",
        files={"audio": ("unknown_xyz.mp3", b"\x00\x01\x02random-bytes", "audio/mpeg")},
    )
    assert r.status_code == 200
    assert r.json()["understanding"]["transcript_source"] == "simulated"


# ---------------------------------------------------------------------------
# f. 审核确认审计
# ---------------------------------------------------------------------------
def test_confirm_audit():
    c = _client()
    r = c.post("/api/cases", json={"text": "测试内容用于审核审计验证。"})
    assert r.status_code == 200
    cid = r.json()["case_id"]
    cf = c.post(f"/api/cases/{cid}/confirm", json={"operator": "测试员"}).json()
    assert cf["confirmed"] is True
    full = c.get(f"/api/cases/{cid}").json()
    assert full["confirmed"] is True
    assert full["audit_log"][-1]["operator"] == "测试员"


# ---------------------------------------------------------------------------
# g. 历史检索
# ---------------------------------------------------------------------------
def test_history_search():
    c = _client()
    r = c.get("/api/history", params={"q": "拖欠工资"})
    assert r.status_code == 200
    body = r.json()
    results = body["results"]
    assert isinstance(results, list) and len(results) > 0
    first = results[0]
    hay = (first.get("category") or "") + (first.get("title") or "") + (
        first.get("request_content") or ""
    )
    assert first.get("category") == "劳动和社会保障" or "工资" in hay
