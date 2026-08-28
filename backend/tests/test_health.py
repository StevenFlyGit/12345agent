from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_health() -> None:
    response = client.get("/health")
    assert response.status_code == 200
    payload = response.json()
    assert payload.get("status") == "ok"
    # /health 同时暴露 LLM 可用性（local-engine 回退时为 False）
    assert "llm_available" in payload
