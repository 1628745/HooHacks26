from app.models.schemas import Issue


def rewrite_code(original_code: str, issues: list[Issue]) -> tuple[str, list[str]]:
    updated = original_code
    diff_hints: list[str] = []

    if any(i.issue_type == "duplicated_context" for i in issues):
        updated = _dedupe_blank_lines(updated)
        diff_hints.append("Removed duplicate empty spacing around repeated context blocks.")

    if any(i.issue_type == "unnecessary_formatting" for i in issues):
        updated = updated.replace(".strip().strip()", ".strip()")
        diff_hints.append("Collapsed repeated formatting calls.")

    if any(i.issue_type == "mergeable_steps" for i in issues):
        updated = updated.replace("\n\n", "\n")
        diff_hints.append("Compacted sequential step declarations where possible.")

    if updated == original_code:
        diff_hints.append("No deterministic rewrite applied; use LLM-assisted rewrite in future iteration.")

    return updated, diff_hints


def _dedupe_blank_lines(text: str) -> str:
    while "\n\n\n" in text:
        text = text.replace("\n\n\n", "\n\n")
    return text
