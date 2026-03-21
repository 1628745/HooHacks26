import ast
from dataclasses import dataclass

from app.services.parser.langchain_locator import locate_langchain_nodes


@dataclass
class ParseResult:
    tree: ast.AST
    langchain_nodes: list[ast.AST]
    notes: list[str]


def parse_code(code: str) -> ParseResult:
    notes: list[str] = []
    try:
        tree = ast.parse(code)
    except SyntaxError as exc:
        raise ValueError(f"Invalid Python syntax: {exc.msg} at line {exc.lineno}") from exc

    langchain_nodes = locate_langchain_nodes(tree)
    if not langchain_nodes:
        notes.append("No explicit LangChain imports/calls found; using generic pipeline extraction.")
    else:
        notes.append(f"Detected {len(langchain_nodes)} LangChain-relevant AST nodes.")

    return ParseResult(tree=tree, langchain_nodes=langchain_nodes, notes=notes)
