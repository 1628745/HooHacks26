from __future__ import annotations

import json
import traceback
from difflib import unified_diff
from queue import Empty, Queue
from threading import Thread

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse

from app.models.schemas import (
    AnalyzeRequest,
    AnalyzeResponse,
    OptimizeRequest,
    OptimizeResponse,
    ValidateRequest,
    ValidateResponse,
)
from app.services.analyzer.inefficiency_rules import detect_issues
from app.services.extractor.pipeline_ir_builder import build_pipeline_ir
from app.services.generator.code_rewriter import rewrite_code
from app.services.metrics.estimator import estimate_metrics
from app.services.optimizer.emit_types import OptimizeEmitFn
from app.services.optimizer.llm_optimizer import build_optimization_explanation
from app.services.optimizer.multi_step_optimize import OptimizationExhausted, run_llm_optimize
from app.services.parser.ast_parser import parse_code
from app.services.llm.openrouter_client import OpenRouterError, generate_text, openrouter_configured
from app.services.validation.syntax_guard import validate_python_syntax

router = APIRouter()

_SSE_HEADERS = {
    "Cache-Control": "no-cache",
    "Connection": "keep-alive",
    "X-Accel-Buffering": "no",
}


def _opt_log(msg: str) -> None:
    print(f"[pipeline-optimize] {msg}", flush=True)


def _sse(data: dict) -> str:
    return f"data: {json.dumps(data, ensure_ascii=False)}\n\n"


def _execute_optimize(
    payload: OptimizeRequest,
    emit: OptimizeEmitFn | None = None,
    log_bucket: dict | None = None,
) -> OptimizeResponse:
    _opt_log("========== optimize execute START ==========")
    _opt_log(f"file_name={payload.file_name!r}, original_code length={len(payload.original_code)}")

    issues = detect_issues(payload.ir)
    if payload.selected_issue_ids:
        issues = [i for i in issues if i.id in set(payload.selected_issue_ids)]

    before = estimate_metrics(payload.ir)
    _opt_log(f"detect_issues → {len(issues)} issues; metrics_before llm_calls={before.llm_calls}")

    event_log: list[str] = []
    if log_bucket is not None:
        log_bucket["event_log"] = event_log

    if openrouter_configured():
        _opt_log("OpenRouter configured — LLM path")
        try:
            explanation, optimized_code, after = run_llm_optimize(
                generate_text,
                payload.file_name,
                payload.original_code,
                payload.ir,
                issues,
                before,
                event_log,
                emit=emit,
            )
            for line in event_log:
                _opt_log(f"event_log | {line}")
            diff_hints: list[str] = ["LLM optimization via OpenRouter (repair loops enabled)."]
        except OptimizationExhausted as exc:
            _opt_log(f"FAIL: OptimizationExhausted: {exc!r}")
            for line in exc.event_log:
                _opt_log(f"event_log | {line}")
            raise
        except OpenRouterError as exc:
            _opt_log(f"FAIL: OpenRouterError: {exc!r}")
            _opt_log(traceback.format_exc())
            raise
        llm_used = True
        issues_applied_ids = [i.id for i in issues] if issues else ["llm-optimize"]
        _opt_log("optimize execute LLM path DONE")
    else:
        _opt_log("Deterministic rewrite path")
        event_log.append("Deterministic rewrite path (OpenRouter not configured).")
        optimized_code, diff_hints = rewrite_code(payload.original_code, issues)
        valid, errors = validate_python_syntax(optimized_code)
        if not valid:
            raise HTTPException(status_code=400, detail=f"Optimized code is invalid Python: {errors}")
        adjusted_calls = max(
            1,
            before.llm_calls - len([i for i in issues if i.issue_type == "mergeable_steps"]),
        )
        after = before.model_copy(
            update={
                "llm_calls": adjusted_calls,
                "token_estimate": max(100, int(before.token_estimate * 0.8)),
                "energy_wh": round(adjusted_calls * 0.3, 3),
            }
        )
        explanation = build_optimization_explanation(issues)
        issues_applied_ids = [i.id for i in issues]
        llm_used = False

    diff_hunks = list(
        unified_diff(
            payload.original_code.splitlines(),
            optimized_code.splitlines(),
            fromfile=f"{payload.file_name}:before",
            tofile=f"{payload.file_name}:after",
            lineterm="",
        )
    )
    diff_hunks.extend(diff_hints)

    _opt_log(f"optimize execute END (llm_used={openrouter_configured() and llm_used})")
    return OptimizeResponse(
        optimized_code=optimized_code,
        issues_applied=issues_applied_ids,
        explanation=explanation,
        metrics_before=before,
        metrics_after=after,
        diff_hunks=diff_hunks,
        llm_used=llm_used,
        optimization_event_log=event_log,
    )


@router.post("/analyze", response_model=AnalyzeResponse)
def analyze_pipeline(payload: AnalyzeRequest) -> AnalyzeResponse:
    try:
        parse_result = parse_code(payload.code)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    ir = build_pipeline_ir(parse_result.tree)
    issues = detect_issues(ir)
    metrics_before = estimate_metrics(ir)
    return AnalyzeResponse(
        ir=ir,
        issues=issues,
        metrics_before=metrics_before,
        parser_notes=parse_result.notes,
    )


@router.post("/optimize", response_model=OptimizeResponse)
def optimize_pipeline(payload: OptimizeRequest) -> OptimizeResponse:
    log_bucket: dict = {}
    try:
        return _execute_optimize(payload, emit=None, log_bucket=log_bucket)
    except OptimizationExhausted as exc:
        raise HTTPException(
            status_code=502,
            detail={
                "message": str(exc),
                "optimization_event_log": exc.event_log,
            },
        ) from exc
    except OpenRouterError as exc:
        elog = log_bucket.get("event_log") or []
        if elog:
            raise HTTPException(
                status_code=502,
                detail={"message": str(exc), "optimization_event_log": elog},
            ) from exc
        raise HTTPException(status_code=502, detail=str(exc)) from exc


def _optimize_stream_generator(payload: OptimizeRequest):
    q: Queue = Queue()

    def emit(level: str, message: str) -> None:
        q.put(("log", level, message))

    log_bucket: dict = {}
    result_holder: dict = {}

    def worker() -> None:
        try:
            result_holder["response"] = _execute_optimize(payload, emit=emit, log_bucket=log_bucket)
        except OptimizationExhausted as exc:
            result_holder["exhausted"] = exc
        except OpenRouterError as exc:
            result_holder["openrouter"] = exc
        except HTTPException as exc:
            result_holder["http"] = exc
        except Exception as exc:
            result_holder["other"] = exc
        finally:
            q.put(("done", None))

    Thread(target=worker, daemon=True).start()

    while True:
        try:
            item = q.get(timeout=7200.0)
        except Empty:
            yield _sse({"event": "fatal", "detail": {"message": "Stream timed out waiting for optimizer."}})
            return

        if item[0] == "log":
            _kind, level, message = item
            yield _sse({"event": "log", "level": level, "message": message})
        elif item[0] == "done":
            break

    if "response" in result_holder:
        resp: OptimizeResponse = result_holder["response"]
        yield _sse({"event": "done", "payload": resp.model_dump()})
        return

    if "exhausted" in result_holder:
        exc: OptimizationExhausted = result_holder["exhausted"]
        yield _sse(
            {
                "event": "fatal",
                "detail": {"message": str(exc), "optimization_event_log": exc.event_log},
            }
        )
        return

    if "openrouter" in result_holder:
        exc: OpenRouterError = result_holder["openrouter"]
        elog = log_bucket.get("event_log") or []
        yield _sse(
            {
                "event": "fatal",
                "detail": {"message": str(exc), "optimization_event_log": elog},
            }
        )
        return

    if "http" in result_holder:
        http_exc: HTTPException = result_holder["http"]
        d = http_exc.detail
        if isinstance(d, dict):
            yield _sse({"event": "fatal", "detail": d})
        else:
            yield _sse({"event": "fatal", "detail": {"message": str(d)}})
        return

    if "other" in result_holder:
        o = result_holder["other"]
        yield _sse({"event": "fatal", "detail": {"message": str(o)}})
        return


@router.post("/optimize-stream")
def optimize_pipeline_stream(payload: OptimizeRequest) -> StreamingResponse:
    if not openrouter_configured():

        def deterministic_gen():
            resp = _execute_optimize(payload, emit=None, log_bucket=None)
            yield _sse(
                {
                    "event": "log",
                    "level": "info",
                    "message": "Deterministic rewrite (no LLM).",
                }
            )
            yield _sse({"event": "done", "payload": resp.model_dump()})

        return StreamingResponse(
            deterministic_gen(),
            media_type="text/event-stream",
            headers=_SSE_HEADERS,
        )

    return StreamingResponse(
        _optimize_stream_generator(payload),
        media_type="text/event-stream",
        headers=_SSE_HEADERS,
    )


@router.post("/validate", response_model=ValidateResponse)
def validate_code(payload: ValidateRequest) -> ValidateResponse:
    valid, errors = validate_python_syntax(payload.code)
    return ValidateResponse(valid=valid, errors=errors)
