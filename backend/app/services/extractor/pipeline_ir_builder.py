import ast

from app.models.schemas import PipelineEdge, PipelineIR, PipelineNode

# Method names that actually execute / stream an LLM (not class names like ChatOpenAI).
_LLM_METHOD_ATTRS = frozenset(
    {
        "invoke",
        "ainvoke",
        "run",
        "arun",
        "predict",
        "predict_messages",
        "batch",
        "abatch",
        "stream",
        "astream",
        "chat",
        "complete",
        "acomplete",
    }
)

_FORMAT_METHOD_ATTRS = frozenset(
    {
        "format",
        "format_messages",
        "strip",
        "replace",
        "split",
        "join",
        "lstrip",
        "rstrip",
    }
)

_PROMPT_METHOD_ATTRS = frozenset(
    {
        "from_template",
        "from_messages",
        "from_prompt",
        "from_prompts",
        "partial",
    }
)

# Constructors / composables — not runtime LLM invocations.
_MODEL_INIT_NAMES = frozenset(
    {
        "ChatOpenAI",
        "ChatAnthropic",
        "ChatOllama",
        "ChatGroq",
        "ChatCohere",
        "ChatVertexAI",
        "ChatGoogleGenerativeAI",
        "AzureChatOpenAI",
        "OpenAI",
        "Ollama",
        "Anthropic",
        "HuggingFacePipeline",
        "HuggingFaceEndpoint",
    }
)

_RUNNABLE_COMPOSABLE_NAMES = frozenset(
    {
        "RunnablePassthrough",
        "RunnableParallel",
        "RunnableSequence",
        "RunnableLambda",
        "RunnableBranch",
        "RunnableMap",
    }
)

_PROMPT_TYPE_NAMES = frozenset(
    {
        "PromptTemplate",
        "ChatPromptTemplate",
        "FewShotPromptTemplate",
        "Prompt",
    }
)


def _node_type_from_call(node: ast.Call) -> str:
    func = node.func
    if isinstance(func, ast.Attribute):
        if func.attr in _LLM_METHOD_ATTRS:
            return "llm_call"
        if func.attr in _FORMAT_METHOD_ATTRS:
            return "formatting"
        if func.attr in _PROMPT_METHOD_ATTRS:
            return "prompt"
        if isinstance(func.value, ast.Name) and func.value.id == "json" and func.attr in ("dumps", "loads"):
            return "formatting"
        return "transform"
    if isinstance(func, ast.Name):
        if func.id in _MODEL_INIT_NAMES or func.id in _RUNNABLE_COMPOSABLE_NAMES:
            return "model_init"
        if func.id in _PROMPT_TYPE_NAMES:
            return "prompt"
        return "transform"
    call_repr = ast.unparse(func) if hasattr(ast, "unparse") else "call"
    return _fallback_node_type_from_repr(call_repr)


def _fallback_node_type_from_repr(call_repr: str) -> str:
    """When func is not Name/Attribute (rare); avoid substring false positives like *Chat* in ChatOpenAI."""
    lowered = call_repr.lower()
    if any(f".{m}" in lowered for m in ("invoke", "ainvoke", "predict", "batch", "stream", "chat")):
        return "llm_call"
    if any(marker in lowered for marker in ("format", "strip", "replace", "split", "join", "json.dumps", "json.loads")):
        return "formatting"
    if "prompt" in lowered:
        return "prompt"
    return "transform"


def build_pipeline_ir(tree: ast.AST) -> PipelineIR:
    nodes: list[PipelineNode] = []
    edges: list[PipelineEdge] = []
    index = 0

    for ast_node in ast.walk(tree):
        if isinstance(ast_node, ast.Call):
            index += 1
            call_repr = ast.unparse(ast_node.func) if hasattr(ast, "unparse") else "call"
            node_id = f"n{index}"
            nodes.append(
                PipelineNode(
                    id=node_id,
                    label=call_repr,
                    node_type=_node_type_from_call(ast_node),
                    code_span=(getattr(ast_node, "lineno", 0), getattr(ast_node, "end_lineno", 0)),
                    metadata={"expression": ast.unparse(ast_node) if hasattr(ast, "unparse") else ""},
                    confidence=0.7,
                )
            )

    for i in range(len(nodes) - 1):
        edges.append(PipelineEdge(source=nodes[i].id, target=nodes[i + 1].id))

    return PipelineIR(nodes=nodes, edges=edges)
