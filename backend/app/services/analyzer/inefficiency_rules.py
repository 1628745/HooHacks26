from app.models.schemas import Issue, PipelineIR


def detect_issues(ir: PipelineIR) -> list[Issue]:
    issues: list[Issue] = []
    issue_index = 0

    for i in range(len(ir.nodes) - 1):
        left = ir.nodes[i]
        right = ir.nodes[i + 1]

        if left.node_type in {"prompt", "transform"} and right.node_type in {"prompt", "transform"}:
            issue_index += 1
            issues.append(
                Issue(
                    id=f"issue-{issue_index}",
                    issue_type="mergeable_steps",
                    severity="medium",
                    title="Sequential steps can be merged",
                    description=f"{left.label} and {right.label} appear to be mergeable prompt/transform stages.",
                    node_ids=[left.id, right.id],
                    suggested_action="Merge these sequential prompt-like steps into one LLM call.",
                )
            )

        if left.node_type == "formatting" and right.node_type == "llm_call":
            issue_index += 1
            issues.append(
                Issue(
                    id=f"issue-{issue_index}",
                    issue_type="unnecessary_formatting",
                    severity="low",
                    title="Possible removable formatting step",
                    description=f"{left.label} may be unnecessary before {right.label}.",
                    node_ids=[left.id],
                    suggested_action="Inline or remove formatting-only preprocessing.",
                )
            )

    seen_labels: dict[str, str] = {}
    for node in ir.nodes:
        norm = node.label.strip().lower()
        if norm in seen_labels:
            issue_index += 1
            issues.append(
                Issue(
                    id=f"issue-{issue_index}",
                    issue_type="duplicated_context",
                    severity="medium",
                    title="Repeated context detected",
                    description=f"{node.label} appears repeated in multiple steps.",
                    node_ids=[seen_labels[norm], node.id],
                    suggested_action="Deduplicate repeated context into shared variable/prompt segment.",
                )
            )
        else:
            seen_labels[norm] = node.id

    return issues
