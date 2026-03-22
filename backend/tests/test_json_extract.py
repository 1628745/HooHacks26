import pytest

from app.services.optimizer.json_extract import extract_json_object


def test_extract_json_from_fence() -> None:
    raw = """Here you go:
```json
{"calls": [{"node_id": "n1", "purpose": "x"}]}
```
"""
    obj = extract_json_object(raw)
    assert obj["calls"][0]["node_id"] == "n1"


def test_extract_json_inline() -> None:
    raw = 'prefix {"a": 1} suffix'
    obj = extract_json_object(raw)
    assert obj == {"a": 1}


def test_extract_json_empty_raises() -> None:
    with pytest.raises(ValueError):
        extract_json_object("   ")
