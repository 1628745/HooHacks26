from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


def test_health() -> None:
    response = client.get("/api/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_analyze() -> None:
    payload = {"file_name": "demo.py", "code": "print('hello')"}
    response = client.post("/api/pipeline/analyze", json=payload)
    assert response.status_code == 200
    body = response.json()
    assert "ir" in body
    assert "code_explanation" in body
    assert isinstance(body["code_explanation"], str)
    assert "llm_call_sites" in body
    assert isinstance(body["llm_call_sites"], list)
