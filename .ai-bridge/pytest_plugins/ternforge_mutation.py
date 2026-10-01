"""Ternforge mutation operators and noise rules for pytest-gremlins.

The engine's native operators change decisions (comparisons, boundaries, boolean
logic, returned values). This module adds the operators the engine lacks, and
everything that keeps a mutant honest before it runs:

* ``statement`` removes a statement with an effect: a call, an attribute or item
  write, a write to a name the function declares ``global`` or ``nonlocal``, an
  augmented assignment, ``raise`` or ``del``. It never removes a plain local name
  binding, so a removal cannot unbind a name.
* ``body`` replaces a function body with a default of its annotated return type,
  the extreme mutation that finds pseudo-tested functions.
* Python's own faults, after PyTation (arXiv 2601.19088), which found most of its
  mutants beyond what Cosmic Ray makes: ``argument`` removes an optional argument of a
  call (never one the callee requires, when the project defines the callee);
  ``condition`` removes one operand of an ``and``/``or``; ``container`` removes an
  element of a list, tuple, set or dict literal; ``conversion`` removes a built-in
  conversion (``int(x)`` → ``x``); ``method`` removes a bound method call used as a
  value (``text.strip()`` → ``text``); ``attribute`` reads another attribute the same
  code reads on the same object whose name is at least half alike, the most similar first
  (``policy.min_wait`` → ``policy.max_wait``). PyTation's removal of an attribute access
  is left out: nearly every such mutant breaks a type and is caught at once.
* ``conditional`` replaces the condition of an ``if``, ``while`` or conditional
  expression with ``True`` or ``False`` (Stryker, PIT), and ``negation`` negates a
  condition that is a plain value, where no other operator reaches (Google's unary
  operator insertion).
* ``identity`` inverts an identity or membership test (``is`` ↔ ``is not``, ``in`` ↔
  ``not in``), as mutmut does; the engine's comparison operator swaps only ``<``,
  ``<=``, ``>``, ``>=``, ``==`` and ``!=``.
* ``slice`` removes one bound of a slice (``items[:n]`` → ``items[:]``), MutPy's slice
  index removal: a cap or a window the code cuts loses its bound.
* Nothing inside a type annotation is mutated, as mutmut leaves annotations alone: an
  annotation changes no call.
* Arid-code rules keep mutants out of code whose change no contract can observe.
* The ``# mutation: <category>[<operators>] <reason>`` pragma suppresses mutants
  visibly, with a category and a reason; a suppressed mutant never runs.

Nothing here judges a contract: the campaign adapter projects the enriched engine
report onto fault classes.
"""

from __future__ import annotations

import ast
import copy
import difflib
import hashlib
import io
import re
import tokenize
from dataclasses import dataclass, field
from pathlib import Path

OPERATOR_NAMES = (
    "comparison", "boundary", "arithmetic", "boolean", "return", "statement", "body",
    "argument", "condition", "conditional", "negation", "container", "conversion", "method", "attribute",
    "identity", "slice",
)
# The prior of operator productivity (Google's: relational, logical, statement removal, then
# the rest, with PyTation's survival rates placing its operators); the recorded verdicts refine
# it, and a pull request reports one survivor per line in that order.
OPERATOR_PRIORITY = (
    "comparison", "identity", "boolean", "condition", "arithmetic", "statement", "argument", "return", "negation",
    "conversion", "container", "boundary", "slice", "method", "attribute", "conditional", "body",
)
# The operators that change a condition as a whole: planted on the test of an if, while or
# conditional expression, never by the engine's own visit of the expression.
TEST_OPERATORS = ("conditional", "negation")
CONVERSIONS = {"int", "float", "str", "bool", "bytes", "list", "tuple", "set", "frozenset", "dict"}
# A literal of these kinds already has the type its conversion returns.
CONVERSION_LITERALS = {
    "str": (ast.JoinedStr,), "list": (ast.List, ast.ListComp), "tuple": (ast.Tuple,), "set": (ast.Set, ast.SetComp),
    "dict": (ast.Dict, ast.DictComp),
}
CONTAINER_REMOVALS = 3
# A copy whose only reader is one call that reads it once, at once (``payload.update(dict(extra))``):
# the receiver's method, by the conversion it reads the same way, on a local bound only to a new one.
COPY_READERS = {"update": {"dict": {"dict"}, "set": {"set", "frozenset", "list", "tuple"}}, "extend": {"list": {"list", "tuple"}}}
# An attribute is swapped only for one whose name is at least this alike (difflib's ratio): the slip
# of ``min_wait`` for ``max_wait``; unrelated names break a type and are caught at once (PyTation
# found 94% of its swaps caught), so they cost a run and teach nothing.
ATTRIBUTE_SIMILARITY = 0.5
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


def _names_declared_outside(node: ast.AST) -> set[str]:
    """The names the function around ``node`` declares ``global`` or ``nonlocal``: writing one is a
    write to state that outlives the call, as an attribute write is (needs ``annotate``'s links)."""
    function = _enclosing(node, (ast.FunctionDef, ast.AsyncFunctionDef))
    if function is None:
        return set()
    return {name for item in _own_nodes(function) if isinstance(item, (ast.Global, ast.Nonlocal)) for name in item.names}


def _writes_only_outer_names(targets: list[ast.expr], node: ast.AST) -> bool:
    if not targets or not all(isinstance(target, ast.Name) for target in targets):
        return False
    outer = _names_declared_outside(node)
    return all(isinstance(target, ast.Name) and target.id in outer for target in targets)


def is_effect_statement(node: ast.AST) -> bool:
    """A statement whose removal loses an effect but cannot unbind a name."""
    if isinstance(node, ast.Expr):
        return _call_of(node) is not None
    if isinstance(node, ast.AugAssign):
        return True
    if isinstance(node, ast.Assign):
        return _writes_only_attributes_or_items(node.targets) or _writes_only_outer_names(node.targets, node)
    if isinstance(node, ast.AnnAssign):
        return node.value is not None and (
            _writes_only_attributes_or_items([node.target]) or _writes_only_outer_names([node.target], node)
        )
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
        return "Remove a statement with an effect (call, attribute or item write, global or nonlocal write, augmented assignment, raise, del)"

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


# --- Python's own faults: what the operators below know of each node ----------------


class Project:
    """Where the project's modules live, each parsed once: enough to see what a callee requires
    and whether a name is a module, without importing anything."""

    def __init__(self, roots) -> None:
        self.roots = [Path(root).resolve() for root in roots]
        self.trees: dict[Path, ast.Module | None] = {}
        self.imported: dict[str, dict[str, tuple[str, str | None]]] = {}

    def module_file(self, name: str) -> Path | None:
        parts = [part for part in name.split(".") if part]
        for root in self.roots:
            base = root.joinpath(*parts) if parts else root
            for candidate in (base.with_suffix(".py"), base / "__init__.py"):
                if parts and candidate.is_file():
                    return candidate
        return None

    def tree(self, path: Path) -> ast.Module | None:
        if path not in self.trees:
            try:
                self.trees[path] = ast.parse(path.read_text())
            except (OSError, SyntaxError, ValueError):
                self.trees[path] = None
        return self.trees[path]

    def module_name(self, path: str) -> str:
        resolved = Path(path).resolve()
        for root in self.roots:
            try:
                relative = resolved.relative_to(root)
            except ValueError:
                continue
            parts = list(relative.with_suffix("").parts)
            if parts and parts[-1] == "__init__":
                parts = parts[:-1]
            return ".".join(parts)
        return ""

    def imports(self, tree: ast.Module, path: str) -> dict[str, tuple[str, str | None]]:
        """What each imported name of a module refers to: (module, name), or (module, None)."""
        if path in self.imported:
            return self.imported[path]
        current = self.module_name(path)
        package = current if Path(path).name == "__init__.py" else current.rpartition(".")[0]
        found: dict[str, tuple[str, str | None]] = {}
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom):
                base = node.module or ""
                if node.level:
                    anchor = package.split(".") if package else []
                    anchor = anchor[: max(0, len(anchor) - (node.level - 1))]
                    base = ".".join([*anchor, *([base] if base else [])])
                for alias in node.names:
                    found[alias.asname or alias.name] = (base, alias.name)
            elif isinstance(node, ast.Import):
                for alias in node.names:
                    found[alias.asname or alias.name.split(".")[0]] = (alias.name if alias.asname else alias.name.split(".")[0], None)
        self.imported[path] = found
        return found

    def definition(self, tree: ast.Module, path: str, name: str, hops: int = 0) -> ast.AST | None:
        """The def or class a module-level name stands for: the module's own, or one a module under the
        roots defines, followed through at most three re-exports (``from .text import preview_text``)."""
        for node in tree.body:
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)) and node.name == name:
                return node
        target = self.imports(tree, path).get(name)
        if not target or target[1] is None or hops > 3:
            return None
        module_path = self.module_file(target[0])
        module_tree = self.tree(module_path) if module_path else None
        return self.definition(module_tree, str(module_path), target[1], hops + 1) if module_tree is not None else None

    def modules(self, tree: ast.Module, path: str) -> set[str]:
        """The names a module binds to modules: ``import x`` and ``from package import module``."""
        return {
            name for name, (module, item) in self.imports(tree, path).items()
            if item is None or self.module_file(f"{module}.{item}") is not None
        }


def _imported_modules(tree: ast.Module) -> set[str]:
    return {alias.asname or alias.name.split(".")[0] for node in ast.walk(tree) if isinstance(node, ast.Import) for alias in node.names}


def _declares_fields(cls: ast.ClassDef) -> bool:
    """A class whose annotated names are its constructor's parameters (a dataclass, attrs or
    pydantic model, a named tuple)."""
    decorators = {(dotted_name(d.func if isinstance(d, ast.Call) else d) or "").split(".")[-1] for d in cls.decorator_list}
    bases = {(dotted_name(base) or "").split(".")[-1] for base in cls.bases}
    return bool(decorators & {"dataclass", "define", "frozen", "attrs", "mutable"}) or bool(bases & {"BaseModel", "NamedTuple"})


def required_parameters(definition: ast.AST | None) -> set[str]:
    """The keyword names a call of a definition cannot leave out; empty when they cannot be known."""
    if isinstance(definition, (ast.FunctionDef, ast.AsyncFunctionDef)):
        arguments = definition.args
        positional = [*arguments.posonlyargs, *arguments.args]
        required = {item.arg for item in positional[: len(positional) - len(arguments.defaults)]}
        required |= {item.arg for item, default in zip(arguments.kwonlyargs, arguments.kw_defaults, strict=True) if default is None}
        return required - {"self", "cls"}
    if isinstance(definition, ast.ClassDef):
        init = next((item for item in definition.body if isinstance(item, ast.FunctionDef) and item.name == "__init__"), None)
        if init is not None:
            return required_parameters(init)
        if _declares_fields(definition):
            return {
                item.target.id for item in definition.body
                if isinstance(item, ast.AnnAssign) and isinstance(item.target, ast.Name) and item.value is None
                and "ClassVar" not in ast.unparse(item.annotation)
            }
    return set()


class _Link:
    """A node's parent, kept so that copying a mutant copies the node and never its whole module."""

    __slots__ = ("node",)

    def __init__(self, node: ast.AST) -> None:
        self.node = node

    def __copy__(self) -> _Link:
        return self

    def __deepcopy__(self, _memo: dict) -> _Link:
        return self


def parent_of(node: ast.AST) -> ast.AST | None:
    link = getattr(node, "_tf_parent", None)
    return link.node if isinstance(link, _Link) else None


def _enclosing(node: ast.AST, kinds: tuple[type, ...]) -> ast.AST | None:
    parent = parent_of(node)
    while parent is not None and not isinstance(parent, kinds):
        parent = parent_of(parent)
    return parent


def _class_attributes(cls: ast.ClassDef) -> set[str]:
    """The data attributes of a class: its annotated or assigned names and what its methods set on ``self``."""
    names = set()
    for item in cls.body:
        if isinstance(item, ast.AnnAssign) and isinstance(item.target, ast.Name):
            names.add(item.target.id)
        elif isinstance(item, ast.Assign):
            names |= {target.id for target in item.targets if isinstance(target, ast.Name)}
    for node in ast.walk(cls):
        if isinstance(node, ast.Attribute) and isinstance(node.ctx, ast.Store) and isinstance(node.value, ast.Name) and node.value.id == "self":
            names.add(node.attr)
    return {name for name in names if not (name.startswith("__") and name.endswith("__"))}


def _is_dunder(name: str) -> bool:
    return name.startswith("__") and name.endswith("__")


# --- what an argument or a conversion cannot change ----------------------------------------
# Trivially equivalent mutants (Kintis et al., TCE: no input can tell them from the original), found
# from the code as written: a mutant that cannot change a run is not planted, and the report counts it.

_NO_VALUE = object()


def _literal(node: ast.AST | None) -> object:
    try:
        return ast.literal_eval(node) if node is not None else _NO_VALUE
    except (ValueError, TypeError, SyntaxError, MemoryError, RecursionError):
        return _NO_VALUE


def _same_value(left: object, right: object) -> bool:
    """Equal values of equal types, all the way down: ``1``, ``1.0`` and ``True`` differ."""
    if type(left) is not type(right):
        return False
    if isinstance(left, (tuple, list)):
        return len(left) == len(right) and all(_same_value(a, b) for a, b in zip(left, right, strict=True))
    if isinstance(left, dict):
        # The types are equal (checked above), which ty does not carry over to ``right``.
        return list(left) == list(right) and all(_same_value(left[key], right[key]) for key in left)  # ty: ignore[not-subscriptable]
    if isinstance(left, (set, frozenset)):
        return left == right and sorted(map(repr, left)) == sorted(map(repr, right))
    return left == right


def parameter_defaults(definition: ast.AST | None) -> dict[str, ast.AST]:
    """The default each optional parameter of a definition has as written: a function's own, or a
    field's in a class that declares its fields (a value, or ``field(default=…)``)."""
    if isinstance(definition, (ast.FunctionDef, ast.AsyncFunctionDef)):
        arguments = definition.args
        positional = [*arguments.posonlyargs, *arguments.args]
        found = {item.arg: default for item, default in zip(positional[len(positional) - len(arguments.defaults):], arguments.defaults, strict=True)}
        found |= {item.arg: default for item, default in zip(arguments.kwonlyargs, arguments.kw_defaults, strict=True) if default is not None}
        return found
    if isinstance(definition, ast.ClassDef):
        init = next((item for item in definition.body if isinstance(item, ast.FunctionDef) and item.name == "__init__"), None)
        if init is not None:
            return parameter_defaults(init)
        if _declares_fields(definition):
            found = {}
            for item in definition.body:
                if not (isinstance(item, ast.AnnAssign) and isinstance(item.target, ast.Name) and item.value is not None):
                    continue
                value = item.value
                if isinstance(value, ast.Call) and (dotted_name(value.func) or "").split(".")[-1] in {"field", "Field"}:
                    value = next((keyword.value for keyword in value.keywords if keyword.arg == "default"), None)
                if value is not None:
                    found[item.target.id] = value
            return found
    return {}


def _parents(root: ast.AST) -> dict[int, ast.AST]:
    return {id(child): parent for parent in ast.walk(root) for child in ast.iter_child_nodes(parent)}


def truth_read(node: ast.AST, parent_of_node=None) -> bool:  # noqa: ANN001
    """Whether only the truth of what an expression gives is read where it stands: the test of an if,
    a while, a conditional expression or an assert, the operand of ``not``, a comprehension's filter,
    or an operand of ``and``/``or`` that stands in such a place itself."""
    parent_of_node = parent_of_node or parent_of
    parent = parent_of_node(node)
    if isinstance(parent, (ast.If, ast.While, ast.IfExp, ast.Assert)) and parent.test is node:
        return True
    if isinstance(parent, ast.UnaryOp) and isinstance(parent.op, ast.Not):
        return True
    if isinstance(parent, ast.comprehension) and any(item is node for item in parent.ifs):
        return True
    return isinstance(parent, ast.BoolOp) and truth_read(parent, parent_of_node)


def _names_read_only(function: ast.AST, name: str, reader, parents: dict[int, ast.AST]) -> bool:  # noqa: ANN001
    """Whether a function never rebinds a name and reads it at least once, each time where ``reader`` says."""
    reads = 0
    for item in ast.walk(function):
        if isinstance(item, (ast.Global, ast.Nonlocal)) and name in item.names:
            return False
        if isinstance(item, ast.arg) and item.arg == name and parents.get(id(item)) is not function.args:
            return False
        if isinstance(item, ast.Name) and item.id == name:
            if not isinstance(item.ctx, ast.Load) or not reader(item):
                return False
            reads += 1
    return reads > 0


def truth_only_parameters(definition: ast.AST | None) -> set[str]:
    """The parameters a function only tests for truth (``if not condition: raise …``)."""
    if not isinstance(definition, (ast.FunctionDef, ast.AsyncFunctionDef)):
        return set()
    cached = getattr(definition, "_tf_truth_only", None)
    if cached is None:
        parents = _parents(definition)
        arguments = definition.args
        names = {item.arg for item in [*arguments.posonlyargs, *arguments.args, *arguments.kwonlyargs]} - {"self", "cls"}
        cached = {
            name for name in names
            if _names_read_only(definition, name, lambda item: truth_read(item, lambda node: parents.get(id(node))), parents)
        }
        definition._tf_truth_only = cached
    return cached


def log_only_parameters(definition: ast.AST | None) -> set[str]:
    """The parameters a function only hands to logging: each read is inside the arguments of a
    logging call or of a call that builds a logging hook, as the arid.logging rule reads them."""
    if not isinstance(definition, (ast.FunctionDef, ast.AsyncFunctionDef)):
        return set()
    cached = getattr(definition, "_tf_log_only", None)
    if cached is None:
        parents = _parents(definition)

        def logged(item: ast.AST) -> bool:
            child, parent = item, parents.get(id(item))
            while parent is not None and parent is not definition:
                if isinstance(parent, ast.Call) and child is not parent.func and (_is_logging_call(parent) or _builds_log_hook(parent)):
                    return True
                child, parent = parent, parents.get(id(parent))
            return False

        arguments = definition.args
        names = {item.arg for item in [*arguments.posonlyargs, *arguments.args, *arguments.kwonlyargs]} - {"self", "cls"}
        cached = {name for name in names if _names_read_only(definition, name, logged, parents)}
        definition._tf_log_only = cached
    return cached


def _positional_names(definition: ast.AST | None, *, bound: bool) -> list[str]:
    if not isinstance(definition, (ast.FunctionDef, ast.AsyncFunctionDef)):
        return []
    names = [item.arg for item in [*definition.args.posonlyargs, *definition.args.args]]
    return names[1:] if bound else names


def only_truth_read(call: ast.Call) -> bool:
    """Whether only the truth of a call's result is read: where it stands, through a local the
    function binds once and only tests, or by a project callee that only tests the parameter."""
    if truth_read(call):
        return True
    parent = parent_of(call)
    if isinstance(parent, ast.keyword):
        owner = parent_of(parent)
        return parent.arg in (getattr(owner, "_tf_truth_parameters", set()) or set())
    if isinstance(parent, ast.Call) and call is not parent.func:
        index = next((position for position, item in enumerate(parent.args) if item is call), None)
        if index is None or any(isinstance(item, ast.Starred) for item in parent.args[:index + 1]):
            return False
        names = getattr(parent, "_tf_positional", []) or []
        return index < len(names) and names[index] in (getattr(parent, "_tf_truth_parameters", set()) or set())
    if isinstance(parent, ast.Assign) and len(parent.targets) == 1 and isinstance(parent.targets[0], ast.Name):
        function = _enclosing(parent, (ast.FunctionDef, ast.AsyncFunctionDef))
        return function is not None and _local_truth_only(function, parent.targets[0].id, parent.targets[0])
    return False


def _local_truth_only(function: ast.AST, name: str, binding: ast.Name) -> bool:
    """Whether a function binds a local once, at ``binding``, and only tests it for truth."""
    reads = 0
    for item in ast.walk(function):
        if isinstance(item, (ast.Global, ast.Nonlocal)) and name in item.names:
            return False
        if isinstance(item, ast.arg) and item.arg == name:
            return False
        if isinstance(item, ast.Name) and item.id == name and item is not binding:
            if not isinstance(item.ctx, ast.Load) or not truth_read(item):
                return False
            reads += 1
    return reads > 0


def read_once_by_local(call: ast.Call) -> bool:
    """Whether a conversion's copy is read once, at once, by one method of a local the function binds
    only to a new container of that method's kind (``payload.update(dict(extra))``)."""
    parent = parent_of(call)
    if not (
        isinstance(parent, ast.Call) and len(parent.args) == 1 and parent.args[0] is call and not parent.keywords
        and isinstance(parent.func, ast.Attribute) and parent.func.attr in COPY_READERS
        and isinstance(parent.func.value, ast.Name) and isinstance(call.func, ast.Name)
    ):
        return False
    function = _enclosing(parent, (ast.FunctionDef, ast.AsyncFunctionDef))
    if function is None:
        return False
    name = parent.func.value.id
    kinds = set()
    for item in ast.walk(function):
        if isinstance(item, (ast.Global, ast.Nonlocal)) and name in item.names:
            return False
        if isinstance(item, ast.arg) and item.arg == name:
            return False
        if isinstance(item, ast.Name) and item.id == name and not isinstance(item.ctx, ast.Load):
            owner = parent_of(item)
            value = owner.value if isinstance(owner, (ast.Assign, ast.AnnAssign)) and len(getattr(owner, "targets", [item])) == 1 else None
            kind = _new_container_kind(value)
            if kind is None:
                return False
            kinds.add(kind)
    return len(kinds) == 1 and call.func.id in COPY_READERS[parent.func.attr].get(kinds.pop(), set())


def _new_container_kind(value: ast.AST | None) -> str | None:
    if isinstance(value, (ast.Dict, ast.DictComp)):
        return "dict"
    if isinstance(value, (ast.List, ast.ListComp)):
        return "list"
    if isinstance(value, (ast.Set, ast.SetComp)):
        return "set"
    if isinstance(value, ast.Call) and isinstance(value.func, ast.Name) and value.func.id in {"dict", "list", "set"}:
        return value.func.id
    return None


def default_valued_keywords(call: ast.Call) -> list[ast.keyword]:
    """The keywords of a call that pass a project callee's default as it is written there; as the
    annotation read them, once the call is annotated."""
    defaulted = getattr(call, "_tf_defaulted", None)
    if defaulted is not None:
        return [keyword for keyword in call.keywords if keyword.arg in defaulted]
    defaults = getattr(call, "_tf_defaults", {}) or {}
    return [
        keyword for keyword in call.keywords
        if keyword.arg in defaults
        and (value := _literal(keyword.value)) is not _NO_VALUE
        and (default := _literal(defaults[keyword.arg])) is not _NO_VALUE
        and _same_value(value, default)
    ]


def _equivalent_conversion(node: ast.Call) -> str:
    """Why removing a conversion cannot change a run, or nothing; as the annotation read it, once
    the call is annotated."""
    known = getattr(node, "_tf_equivalent", None)
    if known is not None:
        return known
    if node.func.id == "bool" and only_truth_read(node):
        return "conversion: only its truth is read"
    if node.func.id in {"dict", "list", "tuple", "set", "frozenset"} and read_once_by_local(node):
        return "conversion: one call reads the copy at once"
    return ""


def equivalent_sites(node: ast.AST) -> list[str]:
    """Why the Python operators plant no mutant on a site of an annotated tree, once per mutant they
    leave out because no input could tell it from the original."""
    if not isinstance(node, ast.Call):
        return []
    required = getattr(node, "_tf_required", set()) or set()
    found = ["argument: passes the callee's default" for keyword in default_valued_keywords(node) if keyword.arg not in required]
    if ConversionRemoval().plantable(node) and (reason := _equivalent_conversion(node)):
        found.append(reason)
    return found


def annotate(tree: ast.Module, path: str = "", project: Project | None = None) -> ast.Module:
    """Mark on each node what the Python operators read: its parent, whether it is the condition
    of an if, while or conditional expression, the keywords a project callee requires, the defaults
    it has and the parameters it only tests or only logs, whether a call stands as a statement or is
    made on a module, and for an attribute read the other attributes the same code reads on the
    same object."""
    if getattr(tree, "_tf_annotated", False):
        return tree
    tree._tf_annotated = True
    for parent in ast.walk(tree):
        for child in ast.iter_child_nodes(parent):
            child._tf_parent = _Link(parent)
        if isinstance(parent, (ast.If, ast.While, ast.IfExp)):
            parent.test._tf_test = True
        # An if without else around one effect statement, read before any mutant rewrites its body.
        if isinstance(parent, ast.If):
            parent.test._tf_single_effect = (
                not parent.orelse and len(parent.body) == 1 and is_effect_statement(parent.body[0])
            )
    modules = project.modules(tree, path) if project is not None else _imported_modules(tree)
    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            parent = parent_of(node)
            node._tf_statement = isinstance(parent, ast.Expr) or (
                isinstance(parent, ast.Await) and isinstance(parent_of(parent), ast.Expr)
            )
            node._tf_awaited = isinstance(parent, ast.Await)
            # The first argument as written, before a mutant of it rewrites it.
            node._tf_first_argument = node.args[0] if node.args else None
            receiver = node.func.value if isinstance(node.func, ast.Attribute) else None
            node._tf_module_receiver = isinstance(receiver, ast.Name) and receiver.id in modules
            definition = None
            bound = False
            if project is not None and isinstance(node.func, ast.Name):
                definition = project.definition(tree, path, node.func.id)
            elif isinstance(receiver, ast.Name) and receiver.id in {"self", "cls"} and isinstance(node.func, ast.Attribute):
                cls = _enclosing(node, (ast.ClassDef,))
                definition = next(
                    (item for item in getattr(cls, "body", []) if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)) and item.name == node.func.attr),
                    None,
                )
                bound = True
            node._tf_required = required_parameters(definition)
            node._tf_defaults = parameter_defaults(definition)
            node._tf_truth_parameters = truth_only_parameters(definition)
            node._tf_log_parameters = log_only_parameters(definition)
            node._tf_positional = _positional_names(definition, bound=bound)
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            reads: dict[str, set[str]] = {}
            attributes = []
            for item in _own_nodes(node):
                if not isinstance(item, ast.Attribute) or _is_dunder(item.attr):
                    continue
                parent = parent_of(item)
                if isinstance(parent, ast.Call) and parent.func is item:
                    continue
                receiver = ast.unparse(item.value)
                if isinstance(item.value, ast.Name) and item.value.id in modules:
                    continue
                reads.setdefault(receiver, set()).add(item.attr)
                if isinstance(item.ctx, ast.Load):
                    attributes.append((item, receiver))
            owner = parent_of(node)
            if isinstance(owner, ast.ClassDef):
                reads["self"] = reads.get("self", set()) | _class_attributes(owner)
            for item, receiver in attributes:
                item._tf_siblings = sorted(reads.get(receiver, set()) - {item.attr})
    # What makes a mutant trivially equivalent is read here, from the code as written: the engine
    # plants its mutants children first, so by the time a call is visited the literal a keyword
    # passes, or the container a local is bound to, may already be a switch between mutants.
    conversion = ConversionRemoval()
    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            node._tf_defaulted = frozenset(keyword.arg for keyword in default_valued_keywords(node))
            node._tf_equivalent = _equivalent_conversion(node) if conversion.plantable(node) else ""
    return tree


def _described(node: ast.AST, text: str) -> ast.AST:
    node._tf_description = text
    return node


class _PythonOperator:
    """What the Python operators share: each mutant carries its own description."""

    name = ""
    description = ""

    def describe(self, _original: ast.AST, mutated: ast.AST) -> str:
        return str(getattr(mutated, "_tf_description", f"{self.name} mutation"))


class ArgumentRemoval(_PythonOperator):
    """Remove an optional keyword argument of a call (PyTation's RemFuncArg)."""

    name = "argument"
    description = "Remove an optional keyword argument of a call"

    def removable(self, node: ast.AST) -> list[int]:
        if not isinstance(node, ast.Call):
            return []
        required = getattr(node, "_tf_required", set()) or set()
        defaulted = {keyword.arg for keyword in default_valued_keywords(node)}
        return [
            index for index, keyword in enumerate(node.keywords)
            if keyword.arg is not None and keyword.arg not in required and keyword.arg not in defaulted
        ]

    def can_mutate(self, node: ast.AST) -> bool:
        return bool(self.removable(node))

    def mutate(self, node: ast.AST) -> list[ast.AST]:
        mutated = []
        for index in self.removable(node):
            call = copy.deepcopy(node)
            keyword = call.keywords.pop(index)
            mutated.append(_described(call, f"removed argument {keyword.arg}={compact(clean_source(keyword.value), 40)}"))
        return mutated


class ConditionOperandRemoval(_PythonOperator):
    """Remove one operand of an ``and`` or ``or`` (PyTation's RemExpCond)."""

    name = "condition"
    description = "Remove one operand of an and/or condition"

    def can_mutate(self, node: ast.AST) -> bool:
        return isinstance(node, ast.BoolOp) and len(node.values) >= 2

    def mutate(self, node: ast.AST) -> list[ast.AST]:
        if not self.can_mutate(node):
            return []
        word = "and" if isinstance(node.op, ast.And) else "or"
        mutated = []
        for index, operand in enumerate(node.values):
            rest = [copy.deepcopy(value) for position, value in enumerate(node.values) if position != index]
            result = rest[0] if len(rest) == 1 else ast.BoolOp(op=copy.deepcopy(node.op), values=rest)
            mutated.append(_described(result, f"removed `{compact(clean_source(operand), 50)}` from the {word}"))
        return mutated


class ConditionalReplacement(_PythonOperator):
    """Replace a condition with ``True`` or ``False`` (Stryker's ConditionalExpression, PIT's
    conditionals); a loop's condition only with ``False``, never into a loop without end."""

    name = "conditional"
    description = "Replace a condition with True or False"

    def can_mutate(self, node: ast.AST) -> bool:
        return bool(getattr(node, "_tf_test", False)) and not isinstance(node, ast.Constant)

    def mutate(self, node: ast.AST) -> list[ast.AST]:
        if not self.can_mutate(node):
            return []
        values = (False,) if isinstance(parent_of(node), ast.While) else (True, False)
        # An if without else around one effect statement: False would repeat the statement mutant.
        if getattr(node, "_tf_single_effect", False):
            values = (True,)
        return [_described(ast.Constant(value=value), f"condition → {value}") for value in values]


class NegationInsertion(_PythonOperator):
    """Negate a condition that is a plain value, where no comparison or boolean operator reaches
    (Google's unary operator insertion)."""

    name = "negation"
    description = "Negate a condition that is a plain value"

    def can_mutate(self, node: ast.AST) -> bool:
        return (
            bool(getattr(node, "_tf_test", False))
            and not isinstance(parent_of(node), ast.While)
            and not isinstance(node, (ast.Compare, ast.BoolOp, ast.Constant))
            and not (isinstance(node, ast.UnaryOp) and isinstance(node.op, ast.Not))
        )

    def mutate(self, node: ast.AST) -> list[ast.AST]:
        if not self.can_mutate(node):
            return []
        return [_described(ast.UnaryOp(op=ast.Not(), operand=copy.deepcopy(node)), "negated the condition")]


class ContainerElementRemoval(_PythonOperator):
    """Remove an element of a list, tuple, set or dict literal (PyTation's RemElCont): the first,
    the middle and the last, never a tuple a statement unpacks or returns, nor a subscript."""

    name = "container"
    description = "Remove an element of a container literal"

    @staticmethod
    def _allowed(node: ast.AST) -> bool:
        parent = parent_of(node)
        if isinstance(node, (ast.List, ast.Tuple)) and not isinstance(node.ctx, ast.Load):
            return False
        if isinstance(node, ast.Tuple) and isinstance(parent, ast.Return):
            return False
        if isinstance(parent, ast.Subscript) and parent.slice is node:
            return False
        if isinstance(parent, ast.Assign) and parent.value is node and any(
            isinstance(target, (ast.Tuple, ast.List)) or (isinstance(target, ast.Name) and target.id == "__all__") for target in parent.targets
        ):
            return False
        return not isinstance(parent, (ast.Starred, ast.JoinedStr, ast.FormattedValue))

    @staticmethod
    def _items(node: ast.AST) -> list:
        if isinstance(node, ast.Dict):
            return [index for index, key in enumerate(node.keys) if key is not None]
        if isinstance(node, (ast.List, ast.Tuple, ast.Set)):
            return list(range(len(node.elts)))
        return []

    def can_mutate(self, node: ast.AST) -> bool:
        return bool(self._items(node)) and self._allowed(node)

    def mutate(self, node: ast.AST) -> list[ast.AST]:
        if not self.can_mutate(node):
            return []
        items = self._items(node)
        chosen = sorted({items[0], items[len(items) // 2], items[-1]})[:CONTAINER_REMOVALS]
        kind = {ast.Dict: "dict", ast.List: "list", ast.Tuple: "tuple", ast.Set: "set"}[type(node)]
        mutated = []
        for index in chosen:
            copied = copy.deepcopy(node)
            if isinstance(copied, ast.Dict):
                removed = f"{clean_source(node.keys[index])}: {clean_source(node.values[index])}"
                del copied.keys[index], copied.values[index]
            else:
                removed = clean_source(node.elts[index])
                del copied.elts[index]
            if isinstance(copied, ast.Set) and not copied.elts:
                copied = ast.Call(func=ast.Name(id="set", ctx=ast.Load()), args=[], keywords=[])
            mutated.append(_described(copied, f"removed `{compact(removed, 50)}` from the {kind}"))
        return mutated


class ConversionRemoval(_PythonOperator):
    """Remove a built-in conversion around a value (PyTation's RemConvFunc), unless the value
    is written as a literal of the conversion's own type."""

    name = "conversion"
    description = "Remove a built-in conversion"

    def plantable(self, node: ast.AST) -> bool:
        """A conversion whose removal is a valid mutant, whether or not it can change a run."""
        if not (isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id in CONVERSIONS):
            return False
        if len(node.args) != 1 or node.keywords or isinstance(node.args[0], ast.Starred) or getattr(node, "_tf_statement", False):
            return False
        value = getattr(node, "_tf_first_argument", None) or node.args[0]
        if isinstance(value, CONVERSION_LITERALS.get(node.func.id, ())):
            return False
        if isinstance(value, ast.Constant) and type(value.value).__name__ == node.func.id:
            return False
        return not (isinstance(value, ast.Call) and isinstance(value.func, ast.Name) and value.func.id == node.func.id)

    def can_mutate(self, node: ast.AST) -> bool:
        return self.plantable(node) and not _equivalent_conversion(node)

    def mutate(self, node: ast.AST) -> list[ast.AST]:
        if not self.can_mutate(node):
            return []
        return [_described(copy.deepcopy(node.args[0]), f"removed {node.func.id}() around `{compact(clean_source(node.args[0]), 50)}`")]


class MethodCallRemoval(_PythonOperator):
    """Leave out a bound method call whose value the code uses (PyTation's RemMetCall): not on a
    module or a class, not awaited, not a statement (the statement operator removes those)."""

    name = "method"
    description = "Remove a bound method call used as a value"

    def can_mutate(self, node: ast.AST) -> bool:
        if not (isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)) or _is_dunder(node.func.attr):
            return False
        if getattr(node, "_tf_statement", False) or getattr(node, "_tf_awaited", False) or getattr(node, "_tf_module_receiver", False):
            return False
        receiver = node.func.value
        if isinstance(receiver, ast.Name) and receiver.id[:1].isupper():
            return False
        return not (isinstance(receiver, ast.Call) and isinstance(receiver.func, ast.Name) and receiver.func.id == "super")

    def mutate(self, node: ast.AST) -> list[ast.AST]:
        if not self.can_mutate(node):
            return []
        return [_described(copy.deepcopy(node.func.value), f"removed .{node.func.attr}(…)")]


class AttributeSwap(_PythonOperator):
    """Read another attribute the same code reads on the same object, the most similar name
    first (PyTation's ChUsedAttr): the slip of ``min`` for ``max``, ``input`` for ``output``."""

    name = "attribute"
    description = "Read another attribute of the same object"

    @staticmethod
    def _alike(node: ast.AST) -> list[str]:
        if not isinstance(node, ast.Attribute) or not isinstance(node.ctx, ast.Load):
            return []
        return [name for name in getattr(node, "_tf_siblings", None) or [] if difflib.SequenceMatcher(None, node.attr, name).ratio() >= ATTRIBUTE_SIMILARITY]

    def can_mutate(self, node: ast.AST) -> bool:
        return bool(self._alike(node))

    def mutate(self, node: ast.AST) -> list[ast.AST]:
        if not self.can_mutate(node):
            return []
        siblings = self._alike(node)
        other = max(siblings, key=lambda name: (difflib.SequenceMatcher(None, node.attr, name).ratio(), [-ord(char) for char in name]))
        swapped = copy.deepcopy(node)
        swapped.attr = other
        receiver = compact(clean_source(node.value), 40)
        return [_described(swapped, f"{receiver}.{node.attr} → {receiver}.{other}")]


class IdentitySwap(_PythonOperator):
    """Invert an identity or membership test (mutmut's ``is`` ↔ ``is not`` and ``in`` ↔ ``not in``):
    the omitted-versus-given and known-versus-unknown decisions the engine's comparison operator does
    not reach."""

    name = "identity"
    description = "Invert an identity or membership test"
    SWAPS: dict[type, type] = {ast.Is: ast.IsNot, ast.IsNot: ast.Is, ast.In: ast.NotIn, ast.NotIn: ast.In}
    WORDS: dict[type, str] = {ast.Is: "is", ast.IsNot: "is not", ast.In: "in", ast.NotIn: "not in"}

    def can_mutate(self, node: ast.AST) -> bool:
        return isinstance(node, ast.Compare) and any(type(op) in self.SWAPS for op in node.ops)

    def mutate(self, node: ast.AST) -> list[ast.AST]:
        if not isinstance(node, ast.Compare):
            return []
        mutated = []
        for index, op in enumerate(node.ops):
            swap = self.SWAPS.get(type(op))
            if swap is None:
                continue
            compare = copy.deepcopy(node)
            compare.ops[index] = swap()
            mutated.append(_described(compare, f"{self.WORDS[type(op)]} to {self.WORDS[swap]}"))
        return mutated


class SliceIndexRemoval(_PythonOperator):
    """Remove one bound of a slice that is read (MutPy's slice index removal): a cap, a window or a
    skipped head loses its bound, ``routes[:limit]`` → ``routes[:]``."""

    name = "slice"
    description = "Remove one bound of a slice"
    BOUNDS = ("lower", "upper", "step")

    def _bounds(self, node: ast.AST) -> list[str]:
        if not (isinstance(node, ast.Subscript) and isinstance(node.ctx, ast.Load) and isinstance(node.slice, ast.Slice)):
            return []
        return [bound for bound in self.BOUNDS if getattr(node.slice, bound) is not None]

    def can_mutate(self, node: ast.AST) -> bool:
        return bool(self._bounds(node))

    def mutate(self, node: ast.AST) -> list[ast.AST]:
        if not isinstance(node, ast.Subscript):
            return []
        mutated = []
        written = compact(clean_source(node.slice), 50)
        for bound in self._bounds(node):
            copied = copy.deepcopy(node)
            setattr(copied.slice, bound, None)
            mutated.append(_described(copied, f"removed the {bound} bound of [{written}]"))
        return mutated


PYTHON_OPERATORS = (
    ArgumentRemoval, ConditionOperandRemoval, ConditionalReplacement, NegationInsertion,
    ContainerElementRemoval, ConversionRemoval, MethodCallRemoval, AttributeSwap,
    IdentitySwap, SliceIndexRemoval,
)


def annotation_spans(tree: ast.AST) -> list[tuple[tuple[int, int], tuple[int, int]]]:
    """Where a module's type annotations are: a parameter's, a return's and an annotated assignment's.
    Nothing there is mutated (mutmut leaves annotations alone): an annotation changes no call."""
    spans = []
    for node in ast.walk(tree):
        annotations: list[ast.expr | None] = []
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            arguments = node.args
            annotations.append(node.returns)
            annotations.extend(argument.annotation for argument in (*arguments.posonlyargs, *arguments.args, *arguments.kwonlyargs))
            annotations.extend(argument.annotation for argument in (arguments.vararg, arguments.kwarg) if argument is not None)
        elif isinstance(node, ast.AnnAssign):
            annotations.append(node.annotation)
        spans.extend(node_span(annotation) for annotation in annotations if annotation is not None)
    return spans


def function_body_spans(tree: ast.AST) -> list[tuple[tuple[int, int], tuple[int, int]]]:
    """Where code runs only when a function is called: every function's and lambda's body. What lies
    outside (module and class bodies, decorators, default values) runs when the module is imported."""
    spans = []
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.body:
            spans.append((node_span(node.body[0])[0], node_span(node.body[-1])[1]))
        elif isinstance(node, ast.Lambda):
            spans.append(node_span(node.body))
    return spans


def within(spans: list[tuple[tuple[int, int], tuple[int, int]]], start: tuple[int, int], end: tuple[int, int]) -> bool:
    return any(span_start <= start and end <= span_end for span_start, span_end in spans)


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
    # A project's own log helpers, public or private (`log_…`, `_log_…`), only log.
    if leaf.lstrip("_").startswith("log_"):
        return True
    if isinstance(call.func, ast.Attribute) and call.func.attr in LOG_METHODS:
        owner = (dotted_name(call.func.value) or "").split(".")[-1].lower()
        return "log" in owner
    return False


def _builds_log_hook(call: ast.Call) -> bool:
    """A call that only builds a logger or a logging callback (``get_logger(…)``,
    ``build_retry_before_sleep_logger(…)``): what it is given changes log records alone."""
    return (dotted_name(call.func) or "").split(".")[-1].endswith("_logger")


def arid_regions(tree: ast.AST, rules: set[str]) -> list[Region]:
    regions = []
    for node in ast.walk(tree):
        call = _call_of(node) if isinstance(node, ast.stmt) else None
        if call is not None and "arid.logging" in rules and _is_logging_call(call):
            regions.append(Region("arid.logging", *node_span(node)))
        if isinstance(node, ast.Call) and "arid.logging" in rules and _builds_log_hook(node):
            regions.append(Region("arid.logging", *node_span(node)))
        # A keyword a project callee only hands to logging (annotated trees only).
        if isinstance(node, ast.Call) and "arid.logging" in rules:
            logged = getattr(node, "_tf_log_parameters", set()) or set()
            regions.extend(Region("arid.logging", *node_span(keyword)) for keyword in node.keywords if keyword.arg in logged)
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
