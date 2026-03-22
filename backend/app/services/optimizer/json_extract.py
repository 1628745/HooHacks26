"""Extract a JSON object from model text (fenced or inline)."""

from __future__ import annotations

import json
import re
from typing import Any


def extract_json_object(raw: str) -> dict[str, Any]:
    text = raw.strip()
    if not text:
        raise ValueError("Empty model response")

    fence = re.search(r"```(?:json)?\s*\r?\n([\s\S]*?)\r?\n```", text, re.IGNORECASE)
    if fence:
        inner = fence.group(1).strip()
        try:
            out = json.loads(inner)
        except json.JSONDecodeError as exc:
            raise ValueError(f"Invalid JSON inside fence: {exc}") from exc
        if not isinstance(out, dict):
            raise ValueError("JSON in fence must be an object")
        return out

    start = text.find("{")
    if start < 0:
        raise ValueError("No JSON object found in response")
    decoder = json.JSONDecoder()
    try:
        obj, _end = decoder.raw_decode(text, start)
    except json.JSONDecodeError as exc:
        raise ValueError(f"Invalid JSON: {exc}") from exc
    if not isinstance(obj, dict):
        raise ValueError("Top-level JSON must be an object")
    return obj
