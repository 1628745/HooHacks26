from pathlib import Path

from app.services.metrics.estimator import estimate_metrics
from app.services.parser.ast_parser import parse_code
from app.services.extractor.pipeline_ir_builder import build_pipeline_ir

_REPO_ROOT = Path(__file__).resolve().parents[2]
_DEFAULT_PIPELINE = _REPO_ROOT / "samples" / "default_pipeline.py"


def test_default_sample_counts_llm_invocations_not_constructors() -> None:
    """Only .invoke(...) counts as llm_call; ChatOpenAI() constructors do not."""
    code = _DEFAULT_PIPELINE.read_text(encoding="utf-8")
    parsed = parse_code(code)
    ir = build_pipeline_ir(parsed.tree)
    assert estimate_metrics(ir).llm_calls == 10


def test_parser_and_ir_extract_calls() -> None:
    code = """
from langchain.chat_models import ChatOpenAI
model = ChatOpenAI()
result = model.invoke("hello")
"""
    parsed = parse_code(code)
    ir = build_pipeline_ir(parsed.tree)
    assert len(parsed.langchain_nodes) >= 1
    assert len(ir.nodes) >= 1
