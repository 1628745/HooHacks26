"""Multi-step LLM optimization with per-phase repair loops."""

from __future__ import annotations

import json
from typing import Any

from app.core.config import settings
from app.models.schemas import Issue, Metrics, PipelineIR
from app.services.extractor.pipeline_ir_builder import build_pipeline_ir
from app.services.metrics.estimator import estimate_metrics
from app.services.optimizer.json_extract import extract_json_object
from app.services.optimizer.llm_prompts import (
    build_multistep_step1_call_purposes_prompt,
    build_multistep_step2_reduced_calls_prompt,
    build_multistep_step3_rewrite_prompt,
    build_optimize_prompt,
)
from app.services.optimizer.llm_response_parser import split_explanation_and_code
from app.services.parser.ast_parser import parse_code
from app.services.optimizer.emit_types import OptimizeEmitFn, notify_emit
from app.services.validation.syntax_guard import validate_python_syntax


class OptimizationExhausted(RuntimeError):
    """Raised when repair loops exhaust without a valid result."""

    def __init__(self, message: str, event_log: list[str]) -> None:
        super().__init__(message)
        self.event_log = event_log


def _llm_node_ids(ir: PipelineIR) -> list[str]:
    return [n.id for n in ir.nodes if n.node_type == "llm_call"]


def _validate_step1(data: dict[str, Any], expected_ids: list[str]) -> None:
    calls = data.get("calls")
    if not isinstance(calls, list) or not calls:
        raise ValueError('"calls" must be a non-empty array')
    exp = set(expected_ids)
    seen: set[str] = set()
    for i, c in enumerate(calls):
        if not isinstance(c, dict):
            raise ValueError(f"calls[{i}] must be an object")
        nid = c.get("node_id")
        purpose = c.get("purpose")
        if not isinstance(nid, str) or not nid:
            raise ValueError(f"calls[{i}].node_id is required")
        if not isinstance(purpose, str) or not purpose.strip():
            raise ValueError(f"calls[{i}].purpose must be a non-empty string")
        if nid in seen:
            raise ValueError(f"duplicate node_id: {nid}")
        seen.add(nid)
    if seen != exp:
        raise ValueError(f"node_id set mismatch missing={exp - seen!r} extra={seen - exp!r}")


def _validate_step2(data: dict[str, Any], expected_ids: list[str]) -> None:
    rc = data.get("reduced_calls")
    if not isinstance(rc, list) or not rc:
        raise ValueError('"reduced_calls" must be a non-empty array')
    exp = set(expected_ids)
    covered: set[str] = set()
    for i, item in enumerate(rc):
        if not isinstance(item, dict):
            raise ValueError(f"reduced_calls[{i}] must be an object")
        ids = item.get("replaces_node_ids")
        if not isinstance(ids, list) or not ids:
            raise ValueError(f"reduced_calls[{i}].replaces_node_ids must be a non-empty array")
        for nid in ids:
            if not isinstance(nid, str):
                raise ValueError("each replaces_node_ids entry must be a string")
            if nid in covered:
                raise ValueError(f"node_id {nid} appears in more than one reduced_call")
            if nid not in exp:
                raise ValueError(f"unknown node_id in plan: {nid}")
            covered.add(nid)
        cp = item.get("combined_purpose")
        if not isinstance(cp, str) or not cp.strip():
            raise ValueError(f"reduced_calls[{i}].combined_purpose is required")
    if covered != exp:
        raise ValueError(f"partition incomplete; missing={exp - covered!r}")

    tcount = data.get("target_llm_call_count")
    if tcount is not None:
        if not isinstance(tcount, int) or tcount != len(rc):
            raise ValueError("target_llm_call_count must equal len(reduced_calls)")


def _finalize_code(
    optimized_code: str,
    event_log: list[str],
    emit: OptimizeEmitFn | None = None,
) -> tuple[str, Metrics]:
    valid, errors = validate_python_syntax(optimized_code)
    if not valid:
        raise ValueError(f"Invalid Python: {'; '.join(errors)}")
    parse_result = parse_code(optimized_code)
    ir_after = build_pipeline_ir(parse_result.tree)
    after = estimate_metrics(ir_after)
    vline = (
        f"Validation OK — optimized file parses; metrics_after llm_calls={after.llm_calls}"
    )
    event_log.append(vline)
    notify_emit(emit, "info", vline)
    return optimized_code, after


def run_single_shot_with_repairs(
    generate_text_fn,
    file_name: str,
    original_code: str,
    ir: PipelineIR,
    issues: list[Issue],
    event_log: list[str],
    emit: OptimizeEmitFn | None = None,
) -> tuple[str, str, Metrics]:
    max_a = settings.optimize_repair_attempts_per_phase
    feedback: str | None = None
    for attempt in range(1, max_a + 1):
        try:
            prompt = build_optimize_prompt(file_name, original_code, ir, issues)
            if feedback:
                prompt = (
                    prompt
                    + "\n\n---\nPREVIOUS ATTEMPT FAILED. Address this and return valid Python in ```python.\n"
                    + feedback
                )
            line_start = f"[single-shot] LLM attempt {attempt}/{max_a}"
            event_log.append(line_start)
            notify_emit(emit, "info", line_start)
            raw = generate_text_fn(prompt)
            explanation, optimized_code = split_explanation_and_code(raw)
            if not optimized_code:
                raise ValueError("No parseable ```python block or module in response")
            oc, after = _finalize_code(optimized_code, event_log, emit=emit)
            line = f"[single-shot] Succeeded on attempt {attempt}"
            event_log.append(line)
            notify_emit(emit, "ok", line)
            return explanation, oc, after
        except Exception as exc:
            msg = f"[single-shot] Attempt {attempt} failed: {exc}"
            event_log.append(msg)
            notify_emit(emit, "error", msg)
            feedback = str(exc)
    raise OptimizationExhausted(
        f"Single-shot optimization failed after {max_a} attempts",
        event_log,
    )


def run_multistep_with_repairs(
    generate_text_fn,
    file_name: str,
    original_code: str,
    ir: PipelineIR,
    issues: list[Issue],
    event_log: list[str],
    llm_ids: list[str],
    emit: OptimizeEmitFn | None = None,
) -> tuple[str, str, Metrics]:
    max_a = settings.optimize_repair_attempts_per_phase

    purposes_obj: dict[str, Any] | None = None
    purposes_raw: str | None = None
    feedback: str | None = None
    for attempt in range(1, max_a + 1):
        try:
            prompt = build_multistep_step1_call_purposes_prompt(
                file_name, original_code, ir, issues, llm_ids, repair_note=feedback
            )
            line_start = f"[step 1 — call purposes] LLM attempt {attempt}/{max_a}"
            event_log.append(line_start)
            notify_emit(emit, "info", line_start)
            raw = generate_text_fn(prompt)
            purposes_obj = extract_json_object(raw)
            _validate_step1(purposes_obj, llm_ids)
            purposes_raw = json.dumps(purposes_obj, indent=2)
            line = f"[step 1] Succeeded on attempt {attempt}"
            event_log.append(line)
            notify_emit(emit, "ok", line)
            break
        except Exception as exc:
            msg = f"[step 1] Attempt {attempt} failed: {exc}"
            event_log.append(msg)
            notify_emit(emit, "error", msg)
            feedback = str(exc)
    else:
        raise OptimizationExhausted(
            f"Step 1 failed after {max_a} attempts",
            event_log,
        )

    assert purposes_obj is not None and purposes_raw is not None

    reduced_obj: dict[str, Any] | None = None
    reduced_raw: str | None = None
    feedback = None
    for attempt in range(1, max_a + 1):
        try:
            prompt = build_multistep_step2_reduced_calls_prompt(
                file_name, purposes_raw, ir, issues, llm_ids, repair_note=feedback
            )
            line_start = f"[step 2 — reduced calls] LLM attempt {attempt}/{max_a}"
            event_log.append(line_start)
            notify_emit(emit, "info", line_start)
            raw = generate_text_fn(prompt)
            reduced_obj = extract_json_object(raw)
            _validate_step2(reduced_obj, llm_ids)
            reduced_raw = json.dumps(reduced_obj, indent=2)
            line = f"[step 2] Succeeded on attempt {attempt}"
            event_log.append(line)
            notify_emit(emit, "ok", line)
            break
        except Exception as exc:
            msg = f"[step 2] Attempt {attempt} failed: {exc}"
            event_log.append(msg)
            notify_emit(emit, "error", msg)
            feedback = str(exc)
    else:
        raise OptimizationExhausted(
            f"Step 2 failed after {max_a} attempts",
            event_log,
        )

    assert reduced_obj is not None and reduced_raw is not None

    feedback = None
    for attempt in range(1, max_a + 1):
        try:
            prompt = build_multistep_step3_rewrite_prompt(
                file_name,
                original_code,
                purposes_raw,
                reduced_raw,
                repair_note=feedback,
            )
            line_start = f"[step 3 — rewrite code] LLM attempt {attempt}/{max_a}"
            event_log.append(line_start)
            notify_emit(emit, "info", line_start)
            raw = generate_text_fn(prompt)
            explanation, optimized_code = split_explanation_and_code(raw)
            if not optimized_code:
                raise ValueError("No parseable ```python block or module in response")
            oc, after = _finalize_code(optimized_code, event_log, emit=emit)
            line = f"[step 3] Succeeded on attempt {attempt}"
            event_log.append(line)
            notify_emit(emit, "ok", line)
            return explanation, oc, after
        except Exception as exc:
            msg = f"[step 3] Attempt {attempt} failed: {exc}"
            event_log.append(msg)
            notify_emit(emit, "error", msg)
            feedback = str(exc)

    raise OptimizationExhausted(
        f"Step 3 failed after {max_a} attempts",
        event_log,
    )


def run_llm_optimize(
    generate_text_fn,
    file_name: str,
    original_code: str,
    ir: PipelineIR,
    issues: list[Issue],
    metrics_before: Metrics,
    event_log: list[str],
    emit: OptimizeEmitFn | None = None,
) -> tuple[str, str, Metrics]:
    threshold = settings.optimize_single_shot_llm_call_threshold
    llm_ids = _llm_node_ids(ir)
    use_single = metrics_before.llm_calls <= threshold or not llm_ids
    if use_single:
        if not llm_ids:
            p = "No llm_call nodes in IR — using single-shot optimizer (cannot partition for multi-step)."
            event_log.append(p)
            notify_emit(emit, "info", p)
        else:
            p = f"Using single-shot optimizer (llm_calls={metrics_before.llm_calls} <= threshold={threshold})."
            event_log.append(p)
            notify_emit(emit, "info", p)
        return run_single_shot_with_repairs(
            generate_text_fn, file_name, original_code, ir, issues, event_log, emit=emit
        )
    p = f"Using three-step optimizer (llm_calls={metrics_before.llm_calls} > threshold={threshold})."
    event_log.append(p)
    notify_emit(emit, "info", p)
    return run_multistep_with_repairs(
        generate_text_fn, file_name, original_code, ir, issues, event_log, llm_ids, emit=emit
    )
