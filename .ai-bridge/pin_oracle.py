"""What a mutation pin may not do to catch its mutant (ADR_0006, amended 2026-10-02).

"Don't mock what you don't own" (Freeman and Pryce, Growing Object-Oriented Software): a test that
changes what a library computes can make a state the library never produces, and its kill then
proves nothing about the project. Three pins did: ``json.loads`` returning an integer key or an
object wrapped in a list, ``check_schema`` removing ``required`` from its argument. A pin still
stands in for the input and output the project does not control: the network and the provider
SDKs, the clock and waits, randomness, files, the locale, the process environment and logging.

A Requirement's pin also hands the typed public API only values its types admit: silencing the type
checker there makes a configuration no caller can write, unless the pin checks that the value is
refused. Asks no model and runs nothing; a new draft that breaks either rule is rejected unrun.
"""

from __future__ import annotations

import ast
import io
import sys
import tokenize
from functools import cache
from importlib import metadata
from pathlib import Path

PROJECT_PACKAGES = frozenset({"llm_router", "tests"})
BOUNDARIES = frozenset({
    # The network and the provider SDKs.
    "httpx", "httpcore", "requests", "urllib3", "aiohttp", "socket", "ssl", "http", "urllib",
    "openai", "google", "gemini_webapi", "browser_cookie3",
    # The clock, waits and randomness.
    "time", "asyncio", "datetime", "random", "uuid", "secrets",
    # Files, the locale, the process environment and logging output.
    "os", "sys", "pathlib", "io", "builtins", "locale", "tempfile", "shutil", "platform", "logging",
})
TYPE_IGNORES = ("type: ignore", "ty: ignore", "pyright: ignore")


@cache
def external_packages() -> frozenset[str]:
    """The top-level names of the standard library and of every installed distribution."""
    return frozenset((set(sys.stdlib_module_names) | set(metadata.packages_distributions())) - PROJECT_PACKAGES)


def _imports(tree: ast.Module) -> dict[str, str]:
    """What each name a draft imports stands for, as a dotted path."""
    found: dict[str, str] = {}
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                found[alias.asname or alias.name.split(".")[0]] = alias.name if alias.asname else alias.name.split(".")[0]
        elif isinstance(node, ast.ImportFrom) and node.module and not node.level:
            for alias in node.names:
                found[alias.asname or alias.name] = f"{node.module}.{alias.name}"
    return found


def _owner(dotted: str, root: Path) -> str | None:
    """The package outside the project a dotted path ends in, or None when the project owns it. A
    path through a project module reaches a library only by an attribute the module imported
    (``….qwenchat.httpx.AsyncClient``)."""
    parts = [part for part in dotted.split(".") if part]
    if not parts:
        return None
    if parts[0] not in PROJECT_PACKAGES:
        return parts[0] if parts[0] in external_packages() else None
    known = 1
    for index in range(len(parts), 0, -1):
        base = root / "src" / Path(*parts[:index])
        if parts[0] == "tests":
            base = root / Path(*parts[:index])
        if base.with_suffix(".py").is_file() or (base / "__init__.py").is_file():
            known = index
            break
    attribute = parts[known] if known < len(parts) else ""
    return attribute if attribute in external_packages() else None


def _target(call: ast.Call, imports: dict[str, str]) -> str | None:
    """What a substitution call replaces, as a dotted path, or None when it names a local object."""
    func = ast.unparse(call.func)
    args = call.args
    if func.endswith(("monkeypatch.setattr", "patch.object")) and len(args) >= 2 and not (
        isinstance(args[0], ast.Constant) and isinstance(args[0].value, str)
    ):
        root_node = args[0]
        while isinstance(root_node, ast.Attribute):
            root_node = root_node.value
        if not isinstance(root_node, ast.Name) or root_node.id not in imports:
            return None
        dotted = imports[root_node.id] + ast.unparse(args[0])[len(root_node.id):]
        name = args[1].value if isinstance(args[1], ast.Constant) and isinstance(args[1].value, str) else "?"
        return f"{dotted}.{name}"
    if (func.endswith("monkeypatch.setattr") or func == "patch" or func.endswith(".patch")) and args and (
        isinstance(args[0], ast.Constant) and isinstance(args[0].value, str)
    ):
        return args[0].value
    return None


def _lines_within(tree: ast.Module, test) -> set[int]:  # noqa: ANN001
    lines: set[int] = set()
    for node in ast.walk(tree):
        if test(node):
            lines.update(range(node.lineno, (node.end_lineno or node.lineno) + 1))
    return lines


def oracle_problems(code: str, root: Path, *, public_only: bool = False) -> list[str]:
    """What a draft does that a pin may not: each library computation it replaces, and for a
    Requirement's pin each line that silences the type checker outside a check that a value is
    refused (``pytest.raises``) or a fake's own signature."""
    try:
        tree = ast.parse(code)
    except SyntaxError:
        return []
    imports = _imports(tree)
    problems = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        target = _target(node, imports)
        owner = _owner(target, root) if target else None
        if owner and owner not in BOUNDARIES:
            problems.append(
                f"replaces `{target}`, a computation of `{owner}`, which the project does not own (a pin may stand in only for "
                "the network, a provider SDK, the clock, randomness, files, the locale, the environment or logging)"
            )
    if public_only:
        refused = _lines_within(tree, lambda node: isinstance(node, (ast.With, ast.AsyncWith)) and any(
            isinstance(item.context_expr, ast.Call) and ast.unparse(item.context_expr.func).endswith("raises") for item in node.items
        ))
        signatures: set[int] = set()
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.body:
                signatures.update(range(node.lineno, node.body[0].lineno))
        try:
            tokens = list(tokenize.generate_tokens(io.StringIO(code).readline))
        except (tokenize.TokenError, SyntaxError):
            tokens = []
        for token in tokens:
            line = token.start[0]
            if token.type == tokenize.COMMENT and any(marker in token.string for marker in TYPE_IGNORES) and line not in refused | signatures:
                problems.append(
                    f"silences the type checker on line {line}: a Requirement's pin hands the public API only values its types "
                    "admit, unless it checks that one is refused (pytest.raises)"
                )
    return problems
