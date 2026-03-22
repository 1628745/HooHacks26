import json

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_optimize_stream_yields_done(monkeypatch) -> None:
    monkeypatch.setattr("app.api.routes_pipeline.openrouter_configured", lambda: False)
    analyze = client.post(
        "/api/pipeline/analyze",
        json={"file_name": "x.py", "code": "print(1)"},
    )
    assert analyze.status_code == 200
    body = analyze.json()
    payload = {"file_name": "x.py", "original_code": "print(1)", "ir": body["ir"]}

    with client.stream("POST", "/api/pipeline/optimize-stream", json=payload) as response:
        assert response.status_code == 200
        raw = response.read().decode()

    assert "event" in raw
    assert "done" in raw
    # Parse last data line
    blocks = [b.strip() for b in raw.split("\n\n") if b.strip().startswith("data:")]
    assert blocks
    last = blocks[-1]
    data = json.loads(last.removeprefix("data: ").strip())
    assert data.get("event") == "done"
    assert "payload" in data
    assert "optimized_code" in data["payload"]
    assert data["payload"].get("optimization_event_log")
