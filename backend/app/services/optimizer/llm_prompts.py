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
