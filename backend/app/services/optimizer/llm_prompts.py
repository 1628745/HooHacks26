"""Prompts sent to OpenRouter (chat completions) for optimization and chat."""

from __future__ import annotations

import json

from app.models.schemas import Issue, PipelineIR


def build_optimize_prompt(
    file_name: str,
    original_code: str,
    ir: PipelineIR,
    issues: list[Issue],
) -> str:
    issues_payload = [
        {
            "id": i.id,
            "type": i.issue_type,
            "title": i.title,
            "description": i.description,
            "suggested_action": i.suggested_action,
            "node_ids": i.node_ids,
        }
        for i in issues
    ]
    ir_payload = {
        "nodes": [n.model_dump() for n in ir.nodes],
        "edges": [e.model_dump() for e in ir.edges],
    }
    return f"""You are an expert Python engineer optimizing LangChain-style pipelines in a SINGLE file.

Goals (MVP):
1. Merge sequential LLM/prompt steps into fewer calls where safe.
2. Remove unnecessary formatting-only steps when they add no value.
3. Deduplicate repeated context (e.g. same system prefix in multiple calls).

Rules:
- Preserve observable behavior and public API of the script unless clearly dead code.
- Keep imports and patterns consistent with the original (LangChain / Runnable / agents as used).
- Output MUST be valid Python that parses with ast.parse.
- Return the COMPLETE optimized file, not a fragment.

File name: {file_name}

Heuristic pipeline IR (from AST; may be imperfect):
{json.dumps(ir_payload, indent=2)[:12000]}

Heuristic issues detected:
{json.dumps(issues_payload, indent=2)[:8000]}

ORIGINAL CODE:
```python
{original_code}
```

Respond in this order:
1) A short plain-English explanation (2–6 sentences) of what you changed and why.
2) Then output the full optimized file inside ONE markdown fenced block:
```python
# full file contents here
```
"""


def build_chat_prompt(
    file_name: str,
    current_code: str,
    conversation_lines: list[str],
) -> str:
    conv = "\n".join(conversation_lines) if conversation_lines else "(no prior messages)"
    return f"""You are assisting a developer editing a single Python file (LangChain-style LLM pipeline).

The user may ask questions or request edits. If you change the code, output the ENTIRE updated file in ONE ```python fenced block. If you only answer conceptually, you may omit a code block.

File: {file_name}

CURRENT CODE:
```python
{current_code}
```

CONVERSATION (most recent last):
{conv}

Answer the user's latest request. If you provide new code, put the complete file in ```python ... ``` only.
"""


def _ir_issues_json(ir: PipelineIR, issues: list[Issue]) -> tuple[str, str]:
    issues_payload = [
        {
            "id": i.id,
            "type": i.issue_type,
            "title": i.title,
            "description": i.description,
            "suggested_action": i.suggested_action,
            "node_ids": i.node_ids,
        }
        for i in issues
    ]
    ir_payload = {
        "nodes": [n.model_dump() for n in ir.nodes],
        "edges": [e.model_dump() for e in ir.edges],
    }
    return json.dumps(ir_payload, indent=2)[:12000], json.dumps(issues_payload, indent=2)[:8000]


def build_multistep_step1_call_purposes_prompt(
    file_name: str,
    original_code: str,
    ir: PipelineIR,
    issues: list[Issue],
    llm_node_ids: list[str],
    repair_note: str | None = None,
) -> str:
    ir_json, issues_json = _ir_issues_json(ir, issues)
    ids_line = ", ".join(llm_node_ids)
    repair = f"\n\nPREVIOUS OUTPUT WAS INVALID. Fix it. Error:\n{repair_note}\n" if repair_note else ""
    return f"""You analyze LangChain-style Python pipelines. Step 1 of 3: describe what each LLM invocation does.

File: {file_name}

LLM call node ids you MUST cover exactly once each (same id strings as in the IR): {ids_line}

Heuristic IR (AST-derived; order may not match source order):
{ir_json}

Issues (hints):
{issues_json}

ORIGINAL CODE:
```python
{original_code}
```

Return a JSON object (you may wrap it in a ```json fenced block), with this shape:
{{
  "calls": [
    {{
      "node_id": "<id from list above>",
      "label": "<e.g. planner.invoke from IR>",
      "purpose": "<one or two sentences: what this call achieves>",
      "inputs_summary": "<what information flows in>",
      "outputs_summary": "<what the next steps consume>"
    }}
  ]
}}

Rules:
- Include exactly one entry per LLM call node id; do not omit or duplicate ids.
- Base purposes on the actual code and prompts, not generic filler.
{repair}"""


def build_multistep_step2_reduced_calls_prompt(
    file_name: str,
    purposes_json: str,
    ir: PipelineIR,
    issues: list[Issue],
    llm_node_ids: list[str],
    repair_note: str | None = None,
) -> str:
    ir_json, issues_json = _ir_issues_json(ir, issues)
    repair = f"\n\nPREVIOUS OUTPUT WAS INVALID. Fix it. Error:\n{repair_note}\n" if repair_note else ""
    return f"""You optimize LangChain-style Python pipelines. Step 2 of 3: plan merged/reduced LLM calls.

File: {file_name}

All LLM node ids in this pipeline: {", ".join(llm_node_ids)}

Step-1 analysis (JSON):
{purposes_json[:16000]}

Heuristic IR:
{ir_json}

Issues:
{issues_json}

Return a JSON object (you may wrap it in a ```json fenced block), with this shape:
{{
  "target_llm_call_count": <integer, at least 1, ideally fewer than current if merges are safe>,
  "reduced_calls": [
    {{
      "id": "rc1",
      "replaces_node_ids": ["n3", "n5"],
      "combined_purpose": "<what the single merged call should accomplish>",
      "prompt_merge_strategy": "<how to combine prompts/context; mention deduping shared system text if relevant>"
    }}
  ],
  "notes": "<optional risks or non-mergeable boundaries>"
}}

Rules:
- Every id in the LLM node id list must appear in exactly one "replaces_node_ids" array (partition).
- Merge only when behavior can stay equivalent; keep separate calls when roles must stay isolated.
- "reduced_calls" length should match "target_llm_call_count".
{repair}"""


def build_multistep_step3_rewrite_prompt(
    file_name: str,
    original_code: str,
    purposes_json: str,
    reduced_plan_json: str,
    repair_note: str | None = None,
) -> str:
    repair = (
        f"\n\nPREVIOUS CODE FAILED VALIDATION. Fix the Python. Error:\n{repair_note}\n"
        if repair_note
        else ""
    )
    return f"""You are an expert Python engineer. Step 3 of 3: implement the optimization plan in code.

File: {file_name}

Call-purpose analysis (JSON):
{purposes_json[:14000]}

Reduced-call plan (JSON):
{reduced_plan_json[:14000]}

ORIGINAL CODE (rewrite this file; preserve imports/style where reasonable):
```python
{original_code}
```

Rules:
- Implement the reduced-call plan: fewer .invoke (or equivalent) steps where the plan specifies merges.
- Preserve observable behavior and public API unless code is clearly dead.
- Output MUST be valid Python (ast.parse).
- Return the COMPLETE optimized file.

Respond in this order:
1) Short plain-English explanation (2–8 sentences) referencing the plan.
2) Full optimized file in ONE markdown fence:
```python
# complete file
```
{repair}"""
