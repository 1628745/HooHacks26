import ast


LANGCHAIN_HINTS = (
    "langchain",
    "ChatOpenAI",
    "LLMChain",
    "PromptTemplate",
    "Runnable",
    "AgentExecutor",
)


def locate_langchain_nodes(tree: ast.AST) -> list[ast.AST]:
    matches: list[ast.AST] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            names = ",".join(alias.name for alias in node.names)
            if any(hint in names for hint in LANGCHAIN_HINTS):
                matches.append(node)
        elif isinstance(node, ast.ImportFrom):
            base = node.module or ""
            names = ",".join(alias.name for alias in node.names)
            if any(hint in f"{base}.{names}" for hint in LANGCHAIN_HINTS):
                matches.append(node)
        elif isinstance(node, ast.Call):
            fn = ast.unparse(node.func) if hasattr(ast, "unparse") else ""
            if any(hint in fn for hint in LANGCHAIN_HINTS):
                matches.append(node)
    return matches
