from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_optimize_without_openrouter_returns_event_log(monkeypatch) -> None:
    """Deterministic path includes optimization_event_log for the UI."""
    monkeypatch.setattr("app.api.routes_pipeline.openrouter_configured", lambda: False)
    analyze = client.post(
        "/api/pipeline/analyze",
        json={"file_name": "x.py", "code": "print(1)"},
    )
    assert analyze.status_code == 200
    body = analyze.json()
    opt = client.post(
        "/api/pipeline/optimize",
        json={
            "file_name": "x.py",
            "original_code": "print(1)",
            "ir": body["ir"],
        },
    )
    assert opt.status_code == 200
    data = opt.json()
    assert "optimization_event_log" in data
    assert isinstance(data["optimization_event_log"], list)
    assert len(data["optimization_event_log"]) >= 1
