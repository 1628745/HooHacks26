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
from app.services.optimizer.llm_prompts import build_optimize_prompt
from app.services.optimizer.llm_response_parser import split_explanation_and_code
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

    if openrouter_configured():
        _opt_log("Step B: OpenRouter is configured — using LLM path")
        try:
            _opt_log("Step C: Building optimize prompt via build_optimize_prompt() ...")
            prompt = build_optimize_prompt(
                payload.file_name,
                payload.original_code,
                payload.ir,
                issues,
            )
            _opt_log(f"Step D: Prompt built, length={len(prompt)} chars")

            _opt_log("Step E: Calling generate_text() (OpenRouter) — see [openrouter] logs below")
            raw = generate_text(prompt)
            _opt_log(f"Step F: generate_text returned; raw length={len(raw)}")
            _opt_log(f"Step G: Raw model text preview (first 1500 chars):\n{raw[:1500]!s}")

            _opt_log("Step H: split_explanation_and_code() ...")
            explanation, optimized_code = split_explanation_and_code(raw)
            _opt_log(
                f"Step I: split result — has optimized_code={optimized_code is not None}, "
                f"explanation length={len(explanation) if explanation else 0}"
            )
            if optimized_code:
                _opt_log(f"Step J: optimized_code length={len(optimized_code)}, preview:\n{optimized_code[:800]!s}")
            if not optimized_code:
                _opt_log("Step FAIL: No parseable Python from model response")
                raise HTTPException(
                    status_code=502,
                    detail="Model did not return parseable Python. Ensure the model outputs a ```python block or raw valid Python.",
                )
            _opt_log("Step K: validate_python_syntax(optimized_code) ...")
            valid, errors = validate_python_syntax(optimized_code)
            _opt_log(f"Step L: syntax valid={valid}, errors={errors}")
            if not valid:
                _opt_log("Step FAIL: Invalid Python from model")
                raise HTTPException(
                    status_code=502,
                    detail=f"Model returned invalid Python: {errors}",
                )
            _opt_log("Step M: parse_code + build_pipeline_ir for metrics_after ...")
            parse_result = parse_code(optimized_code)
            ir_after = build_pipeline_ir(parse_result.tree)
            after = estimate_metrics(ir_after)
            _opt_log(f"Step N: metrics_after llm_calls={after.llm_calls}")
            diff_hints: list[str] = ["LLM optimization via OpenRouter."]
        except OpenRouterError as exc:
            _opt_log(f"Step FAIL: OpenRouterError: {exc!r}")
            _opt_log(traceback.format_exc())
            raise HTTPException(status_code=502, detail=str(exc)) from exc
        llm_used = True
        issues_applied_ids = [i.id for i in issues] if issues else ["llm-optimize"]
        _opt_log("========== POST /api/pipeline/optimize LLM path DONE (returning 200) ==========")
    else:
        _opt_log("OpenRouter NOT configured — deterministic rewrite path (no LLM call)")
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
    )


@router.post("/validate", response_model=ValidateResponse)
def validate_code(payload: ValidateRequest) -> ValidateResponse:
    valid, errors = validate_python_syntax(payload.code)
    return ValidateResponse(valid=valid, errors=errors)
