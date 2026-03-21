import ast


def validate_python_syntax(code: str) -> tuple[bool, list[str]]:
    try:
        ast.parse(code)
        return True, []
    except SyntaxError as exc:
        err = f"{exc.msg} (line {exc.lineno}, col {exc.offset})"
        return False, [err]
