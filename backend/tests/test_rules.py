from app.models.schemas import PipelineEdge, PipelineIR, PipelineNode
from app.services.analyzer.inefficiency_rules import detect_issues


def test_rule_engine_detects_mergeable_steps() -> None:
    ir = PipelineIR(
        nodes=[
            PipelineNode(id="n1", label="prompt_a", node_type="prompt", metadata={}, confidence=0.9, notes=[]),
            PipelineNode(id="n2", label="prompt_b", node_type="prompt", metadata={}, confidence=0.9, notes=[]),
        ],
        edges=[PipelineEdge(source="n1", target="n2")],
    )
    issues = detect_issues(ir)
    assert any(issue.issue_type == "mergeable_steps" for issue in issues)
