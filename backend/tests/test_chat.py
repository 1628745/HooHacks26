from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


def test_chat_returns_503_when_openrouter_not_configured(monkeypatch) -> None:
    monkeypatch.setattr("app.api.routes_chat.openrouter_configured", lambda: False)
    response = client.post(
        "/api/pipeline/chat",
        json={
            "file_name": "demo.py",
            "current_code": "print(1)",
            "messages": [{"role": "user", "content": "Hello"}],
        },
    )
    assert response.status_code == 503
