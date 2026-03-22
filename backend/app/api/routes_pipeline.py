from difflib import unified_diff
import traceback

from fastapi import APIRouter, HTTPException

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
from app.services.optimizer.llm_optimizer import build_optimization_explanation
from app.services.optimizer.multi_step_optimize import OptimizationExhausted, run_llm_optimize
from app.services.parser.ast_parser import parse_code
from app.services.llm.openrouter_client import OpenRouterError, generate_text, openrouter_configured
from app.services.validation.syntax_guard import validate_python_syntax

router = APIRouter()


def _opt_log(msg: str) -> None:
    print(f"[pipeline-optimize] {msg}", flush=True)


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
    _opt_log("========== POST /api/pipeline/optimize START ==========")
    _opt_log(f"file_name={payload.file_name!r}, original_code length={len(payload.original_code)}")

    issues = detect_issues(payload.ir)
    if payload.selected_issue_ids:
        issues = [i for i in issues if i.id in set(payload.selected_issue_ids)]

    before = estimate_metrics(payload.ir)
    _opt_log(f"Step A: detect_issues → {len(issues)} issues; metrics_before llm_calls={before.llm_calls}")

    event_log: list[str] = []

    if openrouter_configured():
        _opt_log("Step B: OpenRouter is configured — using LLM path (multi-step or single-shot)")
        try:
            explanation, optimized_code, after = run_llm_optimize(
                generate_text,
                payload.file_name,
                payload.original_code,
                payload.ir,
                issues,
                before,
                event_log,
            )
            for line in event_log:
                _opt_log(f"event_log | {line}")
            diff_hints: list[str] = ["LLM optimization via OpenRouter (repair loops enabled)."]
        except OptimizationExhausted as exc:
            _opt_log(f"Step FAIL: OptimizationExhausted: {exc!r}")
            for line in exc.event_log:
                _opt_log(f"event_log | {line}")
            raise HTTPException(
                status_code=502,
                detail={
                    "message": str(exc),
                    "optimization_event_log": exc.event_log,
                },
            ) from exc
        except OpenRouterError as exc:
            _opt_log(f"Step FAIL: OpenRouterError: {exc!r}")
            _opt_log(traceback.format_exc())
            if event_log:
                raise HTTPException(
                    status_code=502,
                    detail={
                        "message": str(exc),
                        "optimization_event_log": event_log,
                    },
                ) from exc
            raise HTTPException(status_code=502, detail=str(exc)) from exc
        llm_used = True
        issues_applied_ids = [i.id for i in issues] if issues else ["llm-optimize"]
        _opt_log("========== POST /api/pipeline/optimize LLM path DONE (returning 200) ==========")
    else:
        _opt_log("OpenRouter NOT configured — deterministic rewrite path (no LLM call)")
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

    _opt_log(f"========== POST /api/pipeline/optimize END (llm_used={llm_used}) ==========")
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


@router.post("/validate", response_model=ValidateResponse)
def validate_code(payload: ValidateRequest) -> ValidateResponse:
    valid, errors = validate_python_syntax(payload.code)
    return ValidateResponse(valid=valid, errors=errors)
