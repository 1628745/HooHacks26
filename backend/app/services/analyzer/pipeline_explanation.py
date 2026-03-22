"""Fallback text when LLM narrative is unavailable."""

from __future__ import annotations

from app.models.schemas import PipelineIR


def fallback_code_explanation(ir: PipelineIR) -> str:
    """Heuristic bullet list from the AST-derived IR (no LLM)."""
    if not ir.nodes:
        return (
            "### Pipeline summary\n\n"
            "No LangChain-style calls were detected in this file (the AST walk found no "
            "matching invoke/prompt patterns). The file may still be valid Python."
        )
    lines = [
        "### Static pipeline summary\n",
        "Rough list of calls the extractor found in **walk order**. "
        "The center panel shows LLM invoke sites used for call counts and comparisons.\n",
    ]
    for n in ir.nodes:
        meta = n.metadata if isinstance(n.metadata, dict) else {}
        expr = meta.get("expression", "")
        expr_s = str(expr) if expr else ""
        if len(expr_s) > 220:
            expr_s = expr_s[:220] + "…"
        lines.append(f"- **{n.label}** (`{n.node_type}`){f' — `{expr_s}`' if expr_s else ''}")
    return "\n".join(lines)
