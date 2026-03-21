from app.models.schemas import Issue, PipelineIR


def build_optimization_explanation(issues: list[Issue]) -> str:
    if not issues:
        return "No high-confidence inefficiencies were detected; optimization kept pipeline mostly unchanged."
    return "Applied optimizations for: " + ", ".join(f"{i.issue_type}" for i in issues)


def suggest_rewrite_instructions(ir: PipelineIR, issues: list[Issue]) -> list[str]:
    instructions: list[str] = []
    if any(i.issue_type == "mergeable_steps" for i in issues):
        instructions.append("Merge adjacent prompt-like operations into a single step.")
    if any(i.issue_type == "unnecessary_formatting" for i in issues):
        instructions.append("Remove unnecessary formatting-only intermediary variables.")
    if any(i.issue_type == "duplicated_context" for i in issues):
        instructions.append("Extract duplicated context snippets into one shared variable.")
    if not instructions:
        instructions.append("Keep behavior equivalent while simplifying chain shape.")
    return instructions
