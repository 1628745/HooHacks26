"""OpenRouter API — OpenAI-compatible chat completions (e.g. stepfun/step-3.5-flash)."""

from __future__ import annotations

import json
import traceback
from typing import Any

import requests

from app.core.config import settings


class OpenRouterError(RuntimeError):
    """Raised when OpenRouter returns an error or empty content."""


def _log(msg: str) -> None:
    print(f"[openrouter] {msg}", flush=True)


def _preview(text: str, limit: int = 2000) -> str:
    text = text.replace("\r\n", "\n")
    if len(text) <= limit:
        return text
    return text[:limit] + f"\n... ({len(text)} chars total, truncated for log)"


def _redact_key(key: str) -> str:
    k = key.strip()
    if len(k) <= 8:
        return "***"
    return f"...{k[-4:]}"


def openrouter_configured() -> bool:
    return bool(settings.openrouter_api_key.strip())


def generate_text(prompt: str) -> str:
    """
    POST /chat/completions with a single user message; returns assistant text.
    """
    _log("=== generate_text START ===")
    if not openrouter_configured():
        _log("ERROR: OPENROUTER_API_KEY not set")
        raise OpenRouterError(
            "OpenRouter is not configured. Set OPENROUTER_API_KEY in backend/.env"
        )

    base = settings.openrouter_base_url.rstrip("/")
    url = f"{base}/chat/completions"
    model = settings.openrouter_model.strip()

    headers: dict[str, str] = {
        "Authorization": f"Bearer {settings.openrouter_api_key.strip()}",
        "Content-Type": "application/json",
    }
    if settings.openrouter_http_referer.strip():
        headers["HTTP-Referer"] = settings.openrouter_http_referer.strip()
    if settings.openrouter_app_title.strip():
        headers["X-Title"] = settings.openrouter_app_title.strip()

    payload: dict[str, Any] = {
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
    }

    _log(f"Step 1: POST {url}")
    _log(f"Step 2: model = {model!r}, key (redacted) = {_redact_key(settings.openrouter_api_key)}")
    _log(f"Step 3: prompt length = {len(prompt)} chars")
    _log(f"Step 4: prompt preview:\n{_preview(prompt, 3000)}")
    _log(f"Step 5: timeout = {settings.openrouter_timeout_seconds}s — calling requests.post ...")

    try:
        response = requests.post(
            url,
            headers=headers,
            json=payload,
            timeout=settings.openrouter_timeout_seconds,
        )
        _log(f"Step 6: HTTP status = {response.status_code}")
        raw_body = response.text
        _log(f"Step 7: raw body length = {len(raw_body)} chars")
        _log(f"Step 8: raw body:\n{_preview(raw_body, 12000)}")
        response.raise_for_status()
    except requests.HTTPError as exc:
        resp = getattr(exc, "response", None)
        body = resp.text[:1200] if resp is not None else ""
        _log(f"FAIL: HTTPError {exc!r} body={body!r}")
        raise OpenRouterError(f"OpenRouter HTTP error: {exc}. Body: {body}") from exc
    except requests.RequestException as exc:
        _log(f"FAIL: RequestException: {exc!r}\n{traceback.format_exc()}")
        raise OpenRouterError(f"OpenRouter request failed: {exc}") from exc

    try:
        data = response.json()
    except json.JSONDecodeError as exc:
        raise OpenRouterError(f"OpenRouter returned non-JSON: {response.text[:500]}") from exc

    if isinstance(data, dict) and data.get("error"):
        err = data["error"]
        msg = err.get("message", str(err)) if isinstance(err, dict) else str(err)
        raise OpenRouterError(f"OpenRouter API error: {msg}")

    text = _extract_message_content(data)
    _log(f"Step 9: extracted content length = {len(text)}")
    _log(f"Step 10: extracted content (full):\n{text}")
    if not text.strip():
        err_detail = data.get("error") if isinstance(data, dict) else None
        _log(f"FAIL: empty content, error field = {err_detail!r}")
        raise OpenRouterError(
            "OpenRouter returned empty assistant content. "
            f"Response keys: {list(data.keys()) if isinstance(data, dict) else type(data)}"
        )
    _log("=== generate_text SUCCESS ===")
    return text


def _extract_message_content(data: dict[str, Any]) -> str:
    choices = data.get("choices")
    if isinstance(choices, list) and len(choices) > 0:
        first = choices[0]
        if isinstance(first, dict):
            msg = first.get("message")
            if isinstance(msg, dict) and msg.get("content") is not None:
                return str(msg["content"])
            if first.get("text") is not None:
                return str(first["text"])
    return ""
