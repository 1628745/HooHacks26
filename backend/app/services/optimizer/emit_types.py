"""Optional callback for live optimization progress (e.g. SSE)."""

from __future__ import annotations

from typing import Callable, Literal

OptimizeEmitFn = Callable[[Literal["info", "ok", "error"], str], None]


def notify_emit(
    emit: OptimizeEmitFn | None,
    level: Literal["info", "ok", "error"],
    message: str,
) -> None:
    if emit is None:
        return
    try:
        emit(level, message)
    except Exception:
        pass
