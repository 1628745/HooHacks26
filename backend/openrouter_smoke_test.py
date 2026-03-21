#!/usr/bin/env python3
"""
Minimal OpenRouter connectivity check — does not use analyze/optimize routes.

Run from the backend directory so `app` resolves:
  cd backend && python openrouter_smoke_test.py

Requires OPENROUTER_API_KEY in backend/.env (or environment).
"""

from __future__ import annotations

from app.services.llm.openrouter_client import OpenRouterError, generate_text


def main() -> None:
    prompt = 'Reply with a single word: "pong".'
    print("Calling OpenRouter with a trivial prompt...")
    try:
        text = generate_text(prompt)
    except OpenRouterError as exc:
        print(f"FAIL: {exc}")
        raise SystemExit(1) from exc

    preview = text.strip().replace("\n", " ")[:200]
    print(f"OK — model returned ({len(text)} chars): {preview!r}")
    raise SystemExit(0)


if __name__ == "__main__":
    main()
