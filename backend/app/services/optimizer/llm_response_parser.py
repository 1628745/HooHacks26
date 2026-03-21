"""Parse model text into explanation + optional Python code block."""

from __future__ import annotations

import ast
import re
from typing import Optional, Tuple

# Allow optional newline after opening fence (models sometimes omit it).
_FENCE = re.compile(r"```(?:python|py)?\s*\r?\n?(.*?)```", re.DOTALL | re.IGNORECASE)


def split_explanation_and_code(raw: str) -> Tuple[str, Optional[str]]:
    """
    Extract ```python ... ``` (or plain ```) if present; remainder is explanation.
    If no valid fenced code, try parsing entire trimmed text as Python module.
    """
    text = raw.strip()

    for m in _FENCE.finditer(text):
        candidate = m.group(1).strip()
        if not candidate:
            continue
        try:
            ast.parse(candidate)
            explanation = (text[: m.start()] + text[m.end() :]).strip()
            return explanation or "See optimized code below.", candidate
        except SyntaxError:
            continue

    try:
        ast.parse(text)
        return "Optimized file (full response).", text
    except SyntaxError:
        pass

    return text, None
