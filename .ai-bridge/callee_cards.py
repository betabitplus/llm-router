"""What a call falls back to when a mutant drops one of its keywords (2026-10-02).

A verdict on such a mutant turns on the default the call then takes, and the question used to leave
it out: on 2026-10-01 four verdicts guessed the preview length of py_lib_runtime wrong (160, not 300
or "unbounded"). A model guesses most about the libraries it has seen least ("On Mitigating Code LLM
Hallucinations with API Documentation", 2024), and grounding a question in the API reference it needs
is what De-Hallucinator does for code (Eghbali and Pradel). The card holds one line per dropped
keyword, the callee's signature read from the installed code with ``inspect.signature`` (PEP 362) as
an editor's signature help shows it, never the callee's source: the smallest set of tokens that
settles the question (Anthropic, "Effective context engineering for AI agents"). A callee the code
does not name precisely enough is said to be unknown, so that no verdict rests on an assumed default.

``dropped_keywords`` compares the two versions of the code without importing anything.
``callee_cards.py resolve REQUESTS OUTPUT`` imports the mutated modules, so the builder runs it apart
from itself, in the project's environment.
"""

from __future__ import annotations

import ast
import builtins
import importlib
import inspect
import json
import sys
import textwrap
from collections import Counter
from pathlib import Path

# A default whose text would change from run to run (an object's address) or fill the question.
VALUE_CHARS = 80
# A signature longer than this shows only the dropped keyword's parameter: the rest settles nothing.
SIGNATURE_CHARS = 160
# Callees whose keywords set what the call changes and leave the rest as it was.
REPLACERS = {"dataclasses.replace", "copy.replace"}


def _calls(code: str) -> tuple[Counter, Counter]:
    """How often each callee is called, as written, and how often each of its keywords is passed."""
    try:
        tree = ast.parse(textwrap.dedent(code))
    except SyntaxError:
        return Counter(), Counter()
    calls: Counter = Counter()
    keywords: Counter = Counter()
    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            func = ast.unparse(node.func)
            calls[func] += 1
            keywords.update((func, keyword.arg) for keyword in node.keywords if keyword.arg)
    return calls, keywords


def dropped_keywords(original: str, mutated: str) -> list[tuple[str, str]]:
    """The keywords the changed version no longer passes to a call it still makes, as (callee as
    written, keyword): a call removed whole falls back to nothing, so it drops none."""
    calls, keywords = _calls(original)
    mutated_calls, mutated_keywords = _calls(mutated)
    return sorted(
        (func, keyword) for (func, keyword), count in (keywords - mutated_keywords).items()
        if count and mutated_calls[func] >= calls[func]
    )


def card_text(entries: list[tuple[str, str, dict]]) -> str:
    """The question's section on what each changed call falls back to: one line per dropped keyword."""
    lines = []
    for func, keyword, card in entries:
        if card.get("signature") is not None and card.get("default") is not None:
            lines.append(
                f"- `{card['callee']}{card['signature']}` ({card['where']}): without `{keyword}`, the call takes "
                f"`{keyword}={card['default']}`."
            )
        elif card.get("signature") is not None and card.get("replaces"):
            lines.append(
                f"- `{card['callee']}{card['signature']}` ({card['where']}): it copies its object with the fields its keywords "
                f"name changed, so without `{keyword}` that field keeps the value it has in the object."
            )
        elif card.get("signature") is not None and card.get("kwargs"):
            lines.append(
                f"- `{card['callee']}{card['signature']}` ({card['where']}): `{keyword}` goes to its `**kwargs`, so what the "
                "call takes without it is decided further in and is not shown here; no verdict may rest on an assumed value."
            )
        else:
            lines.append(
                f"- `{func}(…)`: {card.get('unknown') or 'its callee cannot be read'}, so its default for `{keyword}` is not "
                "shown here; no verdict may rest on an assumed one."
            )
    return "What the changed call falls back to:\n" + "\n".join(lines) + "\n" if lines else ""


# --- resolving a callee in the project's environment --------------------------------------------


def _scope(tree: ast.Module, qualname: str) -> ast.AST:
    """The function or class a qualified name stands for in a module, or the module itself."""
    node: ast.AST = tree
    for part in [part for part in qualname.split(".") if part and part != "<module>"]:
        found = next(
            (item for item in ast.iter_child_nodes(node)
             if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)) and item.name == part),
            None,
        )
        if found is None:
            return node
        node = found
    return node


def _owner_class(module: object, qualname: str) -> type | None:
    """The class a method's qualified name sits in: the deepest class along its path."""
    owner, found = module, None
    for part in [part for part in qualname.split(".") if part and part != "<module>"]:
        owner = getattr(owner, part, None)
        if isinstance(owner, type):
            found = owner
        if owner is None:
            break
    return found


def _dotted(namespace: dict, node: ast.AST) -> object | None:
    """A name or a chain of attributes on a module's global, evaluated without calling anything."""
    if isinstance(node, ast.Name):
        return namespace.get(node.id, getattr(builtins, node.id, None))
    if isinstance(node, ast.Attribute):
        base = _dotted(namespace, node.value)
        return getattr(base, node.attr, None) if base is not None else None
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        try:
            return _dotted(namespace, ast.parse(node.value, mode="eval").body)
        except SyntaxError:
            return None
    if isinstance(node, ast.BinOp) and isinstance(node.op, ast.BitOr):
        # ``X | None``: the type it is when it is not None.
        for side in (node.left, node.right):
            if not (isinstance(side, ast.Constant) and side.value is None):
                return _dotted(namespace, side)
    return None


def _local_type(namespace: dict, scope: ast.AST, name: str, line: int) -> type | None:
    """The class a local is bound to last before a line, as the code writes it: built by a
    constructor (also as a ``with`` target, whose ``__enter__`` returns itself), or annotated where
    bound or as a parameter."""
    last_line, written = -1, None
    if isinstance(scope, (ast.FunctionDef, ast.AsyncFunctionDef)):
        for argument in [*scope.args.posonlyargs, *scope.args.args, *scope.args.kwonlyargs]:
            if argument.arg == name and argument.annotation is not None:
                last_line, written = 0, argument.annotation
    for node in ast.walk(scope):
        node_line = getattr(node, "lineno", line)
        if node_line >= line or node_line < last_line:
            continue
        if isinstance(node, ast.Assign) and isinstance(node.value, ast.Call) and any(
            isinstance(target, ast.Name) and target.id == name for target in node.targets
        ):
            last_line, written = node_line, node.value.func
        elif isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name) and node.target.id == name:
            last_line, written = node_line, node.annotation
        elif isinstance(node, (ast.With, ast.AsyncWith)):
            for item in node.items:
                if isinstance(item.optional_vars, ast.Name) and item.optional_vars.id == name and isinstance(item.context_expr, ast.Call):
                    last_line, written = node_line, item.context_expr.func
    found = _dotted(namespace, written) if written is not None else None
    return found if isinstance(found, type) else None


def _attribute_type(namespace: dict, cls: type, name: str) -> type | None:
    """The class an attribute of the class's instances is annotated with."""
    for klass in cls.__mro__:
        annotation = (getattr(klass, "__annotations__", None) or {}).get(name)
        if annotation is None:
            continue
        if isinstance(annotation, type):
            return annotation
        try:
            found = _dotted(vars(sys.modules[klass.__module__]), ast.parse(str(annotation), mode="eval").body)
        except (SyntaxError, KeyError):
            return None
        return found if isinstance(found, type) else None
    return None


def _callee(module: object, scope: ast.AST, qualname: str, call: ast.Call) -> tuple[object | None, bool, str]:
    """What a call calls, whether it is a method reached through an instance (its first parameter
    is then bound), and why it could not be read."""
    namespace = vars(module)
    func = call.func
    if isinstance(func, ast.Name):
        found = _dotted(namespace, func)
        return (found, False, "") if found is not None else (None, False, "the name is not one the module defines or imports")
    if not isinstance(func, ast.Attribute):
        return None, False, "the callee is not a name or an attribute"
    base = func.value
    root = base
    while isinstance(root, ast.Attribute):
        root = root.value
    if not isinstance(root, ast.Name):
        return None, False, "it is called on a value the code computes"
    if root.id in {"self", "cls"}:
        owner = _owner_class(module, qualname)
        if owner is None:
            return None, False, "the class around it cannot be found"
        if base is root:
            return getattr(owner, func.attr, None), root.id == "self", ""
        if isinstance(base, ast.Attribute) and base.value is root:
            kind = _attribute_type(namespace, owner, base.attr)
            if kind is None:
                return None, False, f"the type of `{root.id}.{base.attr}` is not written where the class declares it"
            return getattr(kind, func.attr, None), True, ""
        return None, False, "it is called through a chain of attributes whose types are not written"
    if root.id in namespace or hasattr(builtins, root.id):
        base_object = _dotted(namespace, base)
        if base_object is None:
            return None, False, "the attribute it is called on is not there"
        return getattr(base_object, func.attr, None), not isinstance(base_object, type) and not inspect.ismodule(base_object), ""
    if base is root:
        kind = _local_type(namespace, scope, root.id, call.lineno)
        if kind is None:
            return None, False, f"the type of `{root.id}` is not written where it is bound"
        return getattr(kind, func.attr, None), True, ""
    return None, False, "it is called through a chain of attributes whose types are not written"


class _Text:
    """A text an inspected signature shows as it is, without quotes."""

    def __init__(self, text: str) -> None:
        self.text = text

    def __repr__(self) -> str:
        return self.text


def _value(value: object) -> str:
    text = repr(value)
    if " at 0x" in text:
        return f"<{type(value).__name__}>"
    return text if len(text) <= VALUE_CHARS else text[: VALUE_CHARS - 1] + "…"


def _annotation(annotation: object) -> object:
    if annotation is inspect.Parameter.empty:
        return annotation
    return _Text(annotation if isinstance(annotation, str) else inspect.formatannotation(annotation))


def _where(obj: object) -> str:
    module = str(getattr(obj, "__module__", "") or "")
    top = module.split(".")[0]
    if top in {"llm_router", "tests"}:
        return "the project's own code"
    if top in sys.stdlib_module_names or top == "builtins":
        return "Python's standard library"
    return "a library the project depends on"


def resolve(request: dict) -> dict:
    """One callee's card: its name, its signature as the installed code declares it and the default
    the dropped keyword falls back to; or why it could not be read."""
    try:
        module = importlib.import_module(request["module"])
        tree = ast.parse(Path(inspect.getsourcefile(module) or "").read_text())
    except Exception as error:  # noqa: BLE001 - a module that does not import has no card
        return {"unknown": f"its module does not import here ({type(error).__name__})"}
    scope = _scope(tree, request["qualname"])
    call = next(
        (node for node in ast.walk(scope)
         if isinstance(node, ast.Call) and ast.unparse(node.func) == request["callee"]
         and any(keyword.arg == request["keyword"] for keyword in node.keywords)),
        None,
    )
    if call is None:
        return {"unknown": "the call is not in the code as written"}
    obj, bound, reason = _callee(module, scope, request["qualname"], call)
    if obj is None:
        return {"unknown": reason or "its callee is not there"}
    try:
        signature = inspect.signature(obj)
    except (TypeError, ValueError):
        return {"unknown": "its callee declares no signature Python can read"}
    parameters = list(signature.parameters.values())
    if bound and inspect.isfunction(obj) and parameters and parameters[0].kind in (
        inspect.Parameter.POSITIONAL_ONLY, inspect.Parameter.POSITIONAL_OR_KEYWORD,
    ):
        parameters = parameters[1:]
    shown = signature.replace(
        parameters=[
            parameter.replace(
                annotation=_annotation(parameter.annotation),
                default=parameter.default if parameter.default is inspect.Parameter.empty else _Text(_value(parameter.default)),
            )
            for parameter in parameters
        ],
        return_annotation=_annotation(signature.return_annotation),
    )
    parameter = signature.parameters.get(request["keyword"])
    text = str(shown)
    if len(text) > SIGNATURE_CHARS:
        kept = [item for item in shown.parameters.values() if item.name == request["keyword"] or item.kind is inspect.Parameter.VAR_KEYWORD]
        text = "(…, " + ", ".join(str(item) for item in kept[:1]) + ", …)" + (
            f" -> {shown.return_annotation!r}" if shown.return_annotation is not inspect.Parameter.empty else ""
        )
    name = f"{getattr(obj, '__module__', '') or ''}.{getattr(obj, '__qualname__', '') or getattr(obj, '__name__', '')}".lstrip(".")
    card = {"callee": name, "signature": text, "where": _where(obj), "default": None, "kwargs": False, "replaces": False}
    if parameter is not None and parameter.default is not inspect.Parameter.empty:
        card["default"] = _value(parameter.default)
    elif parameter is None and name in REPLACERS:
        card["replaces"] = True
    elif parameter is None and any(item.kind is inspect.Parameter.VAR_KEYWORD for item in parameters):
        card["kwargs"] = True
    elif parameter is None:
        return {"unknown": f"`{card['callee']}` takes no keyword `{request['keyword']}`"}
    else:
        return {"unknown": f"`{request['keyword']}` has no default in `{card['callee']}`"}
    return card


def main() -> None:
    if len(sys.argv) == 4 and sys.argv[1] == "resolve":
        requests = json.loads(Path(sys.argv[2]).read_text())
        Path(sys.argv[3]).write_text(json.dumps([resolve(request) for request in requests], sort_keys=True) + "\n")
        return
    raise SystemExit("usage: callee_cards.py resolve REQUESTS OUTPUT")


if __name__ == "__main__":
    main()
