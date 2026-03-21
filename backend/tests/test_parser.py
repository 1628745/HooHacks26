from app.services.metrics.estimator import estimate_metrics
from app.services.parser.ast_parser import parse_code
from app.services.extractor.pipeline_ir_builder import build_pipeline_ir


def test_default_sample_counts_two_llm_invocations_not_constructor() -> None:
    """ChatOpenAI() must not count as an llm_call (substring 'chat' false positive)."""
    code = """
from langchain.prompts import PromptTemplate
from langchain.chat_models import ChatOpenAI

model = ChatOpenAI(model="gpt-4o-mini")
prompt_a = PromptTemplate.from_template("Summarize this text: {text}")
prompt_b = PromptTemplate.from_template("Format summary as bullets")

step1 = model.invoke(prompt_a.format(text=input_text))
step2 = model.invoke(prompt_b.format(text=step1))
print(step2)
"""
    parsed = parse_code(code)
    ir = build_pipeline_ir(parsed.tree)
    assert estimate_metrics(ir).llm_calls == 2


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
