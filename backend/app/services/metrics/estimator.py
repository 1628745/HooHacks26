from app.models.schemas import Metrics, PipelineIR


def estimate_metrics(ir: PipelineIR) -> Metrics:
    llm_calls = sum(1 for n in ir.nodes if n.node_type == "llm_call")
    if llm_calls == 0:
        llm_calls = max(1, len(ir.nodes) // 3)
    token_estimate = max(200, llm_calls * 350 + len(ir.nodes) * 40)
    energy_wh = round(llm_calls * 0.3, 3)
    return Metrics(llm_calls=llm_calls, token_estimate=token_estimate, energy_wh=energy_wh)
