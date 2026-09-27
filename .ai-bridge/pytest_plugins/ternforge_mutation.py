"""Ternforge mutation operators and noise rules for pytest-gremlins.

The engine's native operators change decisions (comparisons, boundaries, boolean
logic, returned values). This module adds the two operators behind the Test Plan's
``impl.effect`` class, and everything that keeps a mutant honest before it runs:

* ``statement`` removes a statement with an effect: a call, an attribute or item
  write, an augmented assignment, ``raise`` or ``del``. It never removes a plain
  name binding, so a removal cannot unbind a name.
* ``body`` replaces a function body with a default of its annotated return type,
  the extreme mutation that finds pseudo-tested functions.
* Arid-code rules keep mutants out of code whose change no contract can observe.
* The ``# mutation: <category>[<operators>] <reason>`` pragma suppresses mutants
  visibly, with a category and a reason; a suppressed mutant never runs.

Nothing here judges a contract: the campaign adapter projects the enriched engine
report onto fault classes.
"""

from __future__ import annotations

import ast
import copy
import hashlib
import io
import re
import tokenize
from dataclasses import dataclass, field

OPERATOR_NAMES = ("comparison", "boundary", "boolean", "return", "statement", "body")
# Most productive first (Google's operator productivity: relational, logical, statement
# removal, then the rest); a pull request reports one survivor per line in this order.
OPERATOR_PRIORITY = ("comparison", "boolean", "statement", "return", "boundary", "body")
ARID_RULES = ("arid.logging", "arid.sleep", "arid.type-checking", "arid.repr")
SUPPRESSION_CATEGORIES = ("equivalent", "unproductive", "arid")

LOG_METHODS = {"debug", "info", "warning", "warn", "error", "exception", "critical", "log"}
SLEEP_CALLS = {"sleep", "time.sleep", "asyncio.sleep", "anyio.sleep", "trio.sleep"}
REPR_METHODS = {"__repr__", "__rich_repr__"}
BODY_DUNDERS_ALLOWED = {"__call__"}
STUB_EXCEPTIONS = {"NotImplementedError"}
SKIP_DECORATORS = {"overload", "abstractmethod", "abstractproperty"}


def dotted_name(node: ast.AST | None) -> str | None:
    """``a.b.c`` for a Name/Attribute chain, otherwise None."""
    parts = []
    while isinstance(node, ast.Attribute):
        parts.append(node.attr)
        node = node.value
    if isinstance(node, ast.Name):
        parts.append(node.id)
        return ".".join(reversed(parts))
    return None


def _call_of(statement: ast.stmt) -> ast.Call | None:
    """The call a statement consists of (``f()`` or ``await f()``), if any."""
    if not isinstance(statement, ast.Expr):
        return None
    value = statement.value
    if isinstance(value, ast.Await):
        value = value.value
    return value if isinstance(value, ast.Call) else None


# --- the statement operator --------------------------------------------------------


def _writes_only_attributes_or_items(targets: list[ast.expr]) -> bool:
    return bool(targets) and all(isinstance(target, (ast.Attribute, ast.Subscript)) for target in targets)


def is_effect_statement(node: ast.AST) -> bool:
    """A statement whose removal loses an effect but cannot unbind a name."""
    if isinstance(node, ast.Expr):
        return _call_of(node) is not None
    if isinstance(node, ast.AugAssign):
        return True
    if isinstance(node, ast.Assign):
        return _writes_only_attributes_or_items(node.targets)
    if isinstance(node, ast.AnnAssign):
        return node.value is not None and _writes_only_attributes_or_items([node.target])
    if isinstance(node, ast.Raise):
        return True
    if isinstance(node, ast.Delete):
        return _writes_only_attributes_or_items(node.targets)
    return False


class StatementRemoval:
    """Remove a statement with an effect: the Test Plan's ``impl.effect``."""

    @property
    def name(self) -> str:
        return "statement"

    @property
    def description(self) -> str:
        return "Remove a statement with an effect (call, attribute or item write, augmented assignment, raise, del)"

    def can_mutate(self, node: ast.AST) -> bool:
        return isinstance(node, ast.stmt) and is_effect_statement(node)

    def mutate(self, node: ast.AST) -> list[ast.AST]:
        return [ast.Pass()] if self.can_mutate(node) else []


# --- the body operator -------------------------------------------------------------


def _annotation_node(annotation: ast.expr | None) -> ast.expr | None:
    """A string annotation parsed back into an expression."""
    if isinstance(annotation, ast.Constant) and isinstance(annotation.value, str):
        try:
            return ast.parse(annotation.value, mode="eval").body
        except SyntaxError:
            return None
    return annotation


def _union_members(node: ast.expr) -> list[ast.expr]:
    if isinstance(node, ast.BinOp) and isinstance(node.op, ast.BitOr):
        return [*_union_members(node.left), *_union_members(node.right)]
    if isinstance(node, ast.Subscript) and (dotted_name(node.value) or "").split(".")[-1] == "Union":
        inner = node.slice
        return list(inner.elts) if isinstance(inner, ast.Tuple) else [inner]
    return [node]


def _is_none(node: ast.expr) -> bool:
    return (isinstance(node, ast.Constant) and node.value is None) or dotted_name(node) == "None"


def _const(value) -> ast.expr:
    return ast.Constant(value=value)


def defaults_for_annotation(annotation: ast.expr | None) -> list[tuple[str, ast.expr]]:
    """Type-valid default returns for a return annotation, most informative first."""
    node = _annotation_node(annotation)
    if node is None:
        return []
    members = _union_members(node)
    if len(members) > 1:
        if any(_is_none(member) for member in members):
            return [("None", _const(None))]
        for member in members:
            found = defaults_for_annotation(member)
            if found:
                return found
        return []
    node = members[0]
    if _is_none(node):
        return [("None", _const(None))]
    base = node.value if isinstance(node, ast.Subscript) else node
    name = (dotted_name(base) or "").split(".")[-1]
    if isinstance(node, ast.Subscript) and name == "Optional":
        return [("None", _const(None))]
    simple = {
        "bool": [("False", _const(False)), ("True", _const(True))],
        "int": [("0", _const(0)), ("1", _const(1))],
        "float": [("0.0", _const(0.0))],
        "str": [('""', _const(""))],
        "bytes": [('b""', _const(b""))],
        "Any": [("None", _const(None))],
        "object": [("None", _const(None))],
    }
    if name in simple and not isinstance(node, ast.Subscript):
        return simple[name]
    if name in {"list", "List", "Sequence", "MutableSequence"}:
        return [("[]", ast.List(elts=[], ctx=ast.Load()))]
    if name in {"dict", "Dict", "Mapping", "MutableMapping"}:
        return [("{}", ast.Dict(keys=[], values=[]))]
    if name in {"set", "Set", "AbstractSet", "MutableSet"}:
        return [("set()", ast.Call(func=ast.Name(id="set", ctx=ast.Load()), args=[], keywords=[]))]
    if name in {"frozenset", "FrozenSet"}:
        return [("frozenset()", ast.Call(func=ast.Name(id="frozenset", ctx=ast.Load()), args=[], keywords=[]))]
    if name in {"tuple", "Tuple"}:
        # Only a variadic tuple accepts the empty tuple.
        variadic = not isinstance(node, ast.Subscript) or (
            isinstance(node.slice, ast.Tuple)
            and len(node.slice.elts) == 2
            and isinstance(node.slice.elts[1], ast.Constant)
            and node.slice.elts[1].value is Ellipsis
        )
        return [("()", ast.Tuple(elts=[], ctx=ast.Load()))] if variadic else []
    return []


def _own_nodes(function: ast.AST):
    """Nodes of a function body, without descending into nested scopes."""
    pending = list(ast.iter_child_nodes(function))
    while pending:
        node = pending.pop()
        yield node
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.Lambda, ast.ClassDef)):
            continue
        pending.extend(ast.iter_child_nodes(node))


def _docstring_offset(body: list[ast.stmt]) -> int:
    first = body[0] if body else None
    return int(
        isinstance(first, ast.Expr)
        and isinstance(first.value, ast.Constant)
        and isinstance(first.value.value, str)
    )


def _is_stub(body: list[ast.stmt]) -> bool:
    if not body:
        return True
    if len(body) > 1:
        return False
    only = body[0]
    if isinstance(only, ast.Pass):
        return True
    if isinstance(only, ast.Expr) and isinstance(only.value, ast.Constant) and only.value.value is Ellipsis:
        return True
    if isinstance(only, ast.Raise):
        raised = only.exc.func if isinstance(only.exc, ast.Call) else only.exc
        return (dotted_name(raised) or "").split(".")[-1] in STUB_EXCEPTIONS
    return False


def first_executable(body: list[ast.stmt]) -> ast.stmt | None:
    """The first statement that runs when the body runs (coverage marks its line)."""
    for statement in body[_docstring_offset(body):]:
        if isinstance(statement, (ast.Global, ast.Nonlocal)):
            continue
        if isinstance(statement, ast.Try) and statement.body:
            return first_executable(statement.body) or statement
        return statement
    return None


def body_mutation_plan(function: ast.AST) -> tuple[list[tuple[str, ast.expr]], str | None]:
    """The body's type-valid defaults, or the validity rule that forbids replacing it."""
    if not isinstance(function, (ast.FunctionDef, ast.AsyncFunctionDef)):
        return [], "not a function"
    name = function.name
    if name.startswith("__") and name.endswith("__") and name not in BODY_DUNDERS_ALLOWED:
        return [], "dunder method"
    decorators = {(dotted_name(d.func if isinstance(d, ast.Call) else d) or "").split(".")[-1] for d in function.decorator_list}
    if decorators & SKIP_DECORATORS:
        return [], "overload or abstract method"
    if any(isinstance(node, (ast.Yield, ast.YieldFrom)) for node in _own_nodes(function)):
        return [], "generator"
    body = function.body[_docstring_offset(function.body):]
    if _is_stub(body):
        return [], "stub body"
    if function.returns is None:
        returns_value = any(isinstance(node, ast.Return) and node.value is not None for node in _own_nodes(function))
        defaults = [] if returns_value else [("None", _const(None))]
        if not defaults:
            return [], "no return annotation"
    else:
        defaults = defaults_for_annotation(function.returns)
        if not defaults:
            return [], "no type-valid default"
    if len(body) == 1:
        only = body[0]
        if is_effect_statement(only):
            defaults = [item for item in defaults if item[0] != "None"]
            if not defaults:
                return [], "repeats the statement mutant"
        if isinstance(only, ast.Return):
            defaults = [item for item in defaults if item[0] != "None"]
            if not defaults:
                return [], "repeats the return mutant"
    return defaults, None


class BodyRemoval:
    """Replace a function body with a type-valid default: the Test Plan's ``impl.effect``."""

    @property
    def name(self) -> str:
        return "body"

    @property
    def description(self) -> str:
        return "Replace a function body with a default of its return type"

    def can_mutate(self, node: ast.AST) -> bool:
        return bool(body_mutation_plan(node)[0])

    def mutate(self, node: ast.AST) -> list[ast.AST]:
        return [ast.Return(value=value) for _label, value in body_mutation_plan(node)[0]]


# --- arid code ---------------------------------------------------------------------


@dataclass(frozen=True)
class Region:
    rule: str
    start: tuple[int, int]
    end: tuple[int, int]

    def contains(self, start: tuple[int, int], end: tuple[int, int]) -> bool:
        return self.start <= start and end <= self.end


def node_span(node: ast.AST) -> tuple[tuple[int, int], tuple[int, int]]:
    start_line = min(
        [int(getattr(node, "lineno", 0))]
        + [int(d.lineno) for d in getattr(node, "decorator_list", []) or []]
    )
    start_col = 0 if start_line != int(getattr(node, "lineno", 0)) else int(getattr(node, "col_offset", 0))
    end = (int(getattr(node, "end_lineno", None) or getattr(node, "lineno", 0)), int(getattr(node, "end_col_offset", None) or 0))
    return (start_line, start_col), end


def _is_logging_call(call: ast.Call) -> bool:
    name = dotted_name(call.func) or ""
    if name == "warnings.warn":
        return True
    leaf = name.split(".")[-1]
    if leaf.startswith("log_"):
        return True
    if isinstance(call.func, ast.Attribute) and call.func.attr in LOG_METHODS:
        owner = (dotted_name(call.func.value) or "").split(".")[-1].lower()
        return "log" in owner
    return False


def arid_regions(tree: ast.AST, rules: set[str]) -> list[Region]:
    regions = []
    for node in ast.walk(tree):
        call = _call_of(node) if isinstance(node, ast.stmt) else None
        if call is not None and "arid.logging" in rules and _is_logging_call(call):
            regions.append(Region("arid.logging", *node_span(node)))
        if call is not None and "arid.sleep" in rules and (dotted_name(call.func) or "") in SLEEP_CALLS:
            regions.append(Region("arid.sleep", *node_span(node)))
        if (
            isinstance(node, ast.If)
            and "arid.type-checking" in rules
            and (dotted_name(node.test) or "").split(".")[-1] == "TYPE_CHECKING"
            and node.body
        ):
            last = node.body[-1]
            regions.append(Region("arid.type-checking", node_span(node)[0], node_span(last)[1]))
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and "arid.repr" in rules and node.name in REPR_METHODS:
            regions.append(Region("arid.repr", *node_span(node)))
    return regions


# --- the suppression pragma --------------------------------------------------------

PRAGMA = re.compile(r"#\s*mutation:\s*(?P<body>.*?)\s*$")
PRAGMA_BODY = re.compile(r"^(?P<category>[a-z-]+)(?:\[(?P<operators>[^\]]*)\])?(?:\s+(?P<reason>\S.*))?$")


@dataclass
class Pragma:
    line: int
    category: str
    operators: tuple[str, ...]
    reason: str
    inline: bool
    region: Region | None = None
    error: str | None = None
    matched: int = 0
    mutants: list[str] = field(default_factory=list)

    def covers(self, operator: str, anchor: int, start: tuple[int, int], end: tuple[int, int]) -> bool:
        """An inline pragma covers the mutants anchored on its line (a body mutant is
        anchored on its ``def`` line); a pragma above a statement covers the mutants
        inside that statement."""
        if self.error or (self.operators and operator not in self.operators):
            return False
        if self.inline:
            return anchor == self.line
        return self.region is not None and self.region.contains(start, end)

    def record(self) -> dict:
        return {
            "line": self.line,
            "category": self.category,
            "operators": list(self.operators),
            "reason": self.reason,
            "inline": self.inline,
            "error": self.error,
            "matched": self.matched,
        }


def _statement_starting_at(tree: ast.AST, line: int) -> ast.stmt | None:
    best = None
    for node in ast.walk(tree):
        if isinstance(node, ast.stmt) and node_span(node)[0][0] == line:
            if best is None or node_span(node)[1] > node_span(best)[1]:
                best = node
    return best


def parse_pragmas(source: str, tree: ast.AST | None = None) -> list[Pragma]:
    """Every ``# mutation:`` comment in a module, with what it covers or why it is ignored."""
    tree = tree or ast.parse(source)
    lines = source.splitlines()
    found = []
    try:
        tokens = list(tokenize.generate_tokens(io.StringIO(source).readline))
    except (tokenize.TokenError, SyntaxError):
        return found
    for token in tokens:
        if token.type != tokenize.COMMENT:
            continue
        match = PRAGMA.match(token.string)
        if not match:
            continue
        line = token.start[0]
        inline = bool(lines[line - 1][: token.start[1]].strip())
        body = PRAGMA_BODY.match(match.group("body"))
        category = body.group("category") if body else match.group("body").split(" ", 1)[0]
        operators = tuple(
            item.strip() for item in ((body.group("operators") if body else "") or "").split(",") if item.strip()
        )
        reason = ((body.group("reason") if body else "") or "").strip()
        pragma = Pragma(line=line, category=category, operators=operators, reason=reason, inline=inline)
        if body is None or category not in SUPPRESSION_CATEGORIES:
            pragma.error = f"unknown category {category!r} (use {', '.join(SUPPRESSION_CATEGORIES)})"
        elif not reason:
            pragma.error = "no reason"
        elif set(operators) - set(OPERATOR_NAMES):
            pragma.error = "unknown operator " + ", ".join(sorted(set(operators) - set(OPERATOR_NAMES)))
        if not inline and pragma.error is None:
            target = line + 1
            while target <= len(lines) and (not lines[target - 1].strip() or lines[target - 1].lstrip().startswith("#")):
                target += 1
            statement = _statement_starting_at(tree, target) if target <= len(lines) else None
            if statement is None:
                pragma.error = "no statement follows the pragma"
            else:
                pragma.region = Region("pragma", *node_span(statement))
        found.append(pragma)
    return found


# --- identity, location and replacement of a mutant --------------------------------


def source_segment(lines: list[str], start: tuple[int, int], end: tuple[int, int]) -> str:
    if not lines or start[0] < 1:
        return ""
    if start[0] == end[0]:
        return lines[start[0] - 1][start[1] : end[1]]
    parts = [lines[start[0] - 1][start[1] :]]
    parts.extend(lines[start[0] : end[0] - 1])
    parts.append(lines[end[0] - 1][: end[1]])
    return "\n".join(parts)


def compact(text: str, limit: int = 80) -> str:
    text = " ".join(text.split())
    return text if len(text) <= limit else text[: limit - 1] + "…"


class _Unswitch(ast.NodeTransformer):
    """Collapse the engine's switching expressions back to the original code."""

    @staticmethod
    def _is_switch(test: ast.AST) -> bool:
        return (
            isinstance(test, ast.Compare)
            and isinstance(test.left, ast.Name)
            and test.left.id == "__gremlin_active__"
        )

    def visit_IfExp(self, node: ast.IfExp) -> ast.AST:
        self.generic_visit(node)
        return node.orelse if self._is_switch(node.test) else node

    def visit_If(self, node: ast.If):
        self.generic_visit(node)
        if self._is_switch(node.test):
            return node.orelse or ast.Pass()
        return node


def clean_source(node: ast.AST) -> str:
    cleaned = _Unswitch().visit(copy.deepcopy(node))
    if isinstance(cleaned, list):
        cleaned = cleaned[0] if cleaned else ast.Pass()
    try:
        return ast.unparse(ast.fix_missing_locations(cleaned))
    except Exception:
        return ""


def qualname_index(tree: ast.AST) -> list[tuple[tuple[int, int], tuple[int, int], str]]:
    scopes = []

    def walk(node: ast.AST, prefix: str) -> None:
        for child in ast.iter_child_nodes(node):
            if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                name = f"{prefix}.{child.name}" if prefix else child.name
                scopes.append((*node_span(child), name))
                walk(child, name)
            else:
                walk(child, prefix)

    walk(tree, "")
    return scopes


def enclosing_qualname(index, start: tuple[int, int], end: tuple[int, int]) -> str:
    best = ""
    best_size = None
    for scope_start, scope_end, name in index:
        if scope_start <= start and end <= scope_end:
            size = (scope_end[0] - scope_start[0], scope_end[1] - scope_start[1])
            if best_size is None or size < best_size:
                best, best_size = name, size
    return best or "<module>"


def fingerprint(*parts: object) -> str:
    return hashlib.sha256("|".join(str(part) for part in parts).encode()).hexdigest()[:16]
