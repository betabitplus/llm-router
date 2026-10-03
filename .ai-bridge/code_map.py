"""The code map: every function of the product, bottom-up, with the requirement it serves (history 061).

Ownership is per function, as in BMW LOBSTER's function tracing: a function serves the contracts
whose @impl marker sits on it or inside it (a marker covers its whole function, ADR_0008); a
function no marker names serves the contracts of the functions that call it (a helper inherits its
callers' owners); and a function that serves none is unowned, unless the owner's delegate recorded
why it needs no requirement (`.ai-bridge/code-exemptions.json`). The function list and which test
runs which line come from coverage.py (its per-function regions and line contexts); a test counts
for a contract when it verifies the contract or one derived from it. Vulture names the code nothing
uses. The lines no test runs resolve into DO-178C's four causes (6.4.4.3): no test of the
requirement that owns them, no requirement, extraneous code, and code kept deactivated on purpose.

The call graph that carries ownership to helpers is the module's own, small and static (labelled,
not a tool's): it resolves plain names, `self.`/`cls.` methods of the same class and module
attributes the file imports, and leaves anything dynamic unresolved, so a helper reached only
dynamically stays unowned rather than borrowing an owner it may not have.
"""

from __future__ import annotations

import ast
import json
import re
import subprocess
from collections import defaultdict
from pathlib import Path

VULTURE = "vulture==2.16"
# What vulture reports that the map counts: code nothing in the package uses or reaches.
VULTURE_KINDS = ("function", "method", "class", "unreachable")
CAUSES = ("no-test", "no-requirement", "extraneous", "deactivated")
CAUSE_WORDS = {
    "no-test": "No test",
    "no-requirement": "No requirement",
    "extraneous": "Extraneous",
    "deactivated": "Deactivated",
}
STATES = ("served", "untested", "inherited", "exempt", "unowned", "unused")
# The four questions the Code map asks of every function and class, each answered with one value; the
# values each layer fails on (ADR_0008).
LAYERS = {
    "owner": ("marked", "helper", "exempt", "none"),
    "run": ("run", "not-run", "na"),
    "used": ("used", "unused"),
    "lines": ("clean", "deactivated", "no-test", "no-requirement", "extraneous"),
}
FAILING = {"owner": ("none",), "run": ("not-run",), "used": ("unused",), "lines": ("no-test", "no-requirement", "extraneous")}


def _module_name(path: str) -> str:
    return path.removeprefix("src/").removesuffix(".py").replace("/", ".").removesuffix(".__init__")


def _functions_in(tree: ast.AST) -> dict[str, ast.AST]:
    """Every function and method of a module by its qualified name, nested ones included."""
    found: dict[str, ast.AST] = {}

    def visit(node: ast.AST, prefix: str) -> None:
        for child in ast.iter_child_nodes(node):
            if isinstance(child, ast.ClassDef):
                visit(child, f"{prefix}{child.name}.")
            elif isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef)):
                found[f"{prefix}{child.name}"] = child
                visit(child, f"{prefix}{child.name}.")

    visit(tree, "")
    return found


def _imports(tree: ast.Module, module: str, package: str) -> tuple[dict[str, tuple[str, str]], dict[str, str]]:
    """Names a module imports from the package: plain names to (module, name), and module aliases."""
    names: dict[str, tuple[str, str]] = {}
    modules: dict[str, str] = {}
    parent = module.rsplit(".", 1)[0]
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom):
            base = node.module or ""
            if node.level:
                parts = parent.split(".")
                base = ".".join(parts[: len(parts) - node.level + 1] + ([base] if base else []))
            if base != package and not base.startswith(f"{package}."):
                continue
            for alias in node.names:
                names[alias.asname or alias.name] = (base, alias.name)
                modules[alias.asname or alias.name] = f"{base}.{alias.name}"
        elif isinstance(node, ast.Import):
            for alias in node.names:
                if alias.name == package or alias.name.startswith(f"{package}."):
                    modules[alias.asname or alias.name] = alias.name
    return names, modules


class CodeIndex:
    """The package's functions and classes by module, and what a piece of code names among them."""

    def __init__(self, root: Path, files: list[str], package: str):
        self.functions: dict[str, dict[str, ast.AST]] = {}
        self.paths: dict[str, str] = {}
        self.trees: dict[str, ast.Module] = {}
        self.imports: dict[str, tuple[dict, dict]] = {}
        for path in files:
            tree = ast.parse((root / path).read_text())
            module = _module_name(path)
            self.trees[module], self.paths[module] = tree, path
            self.functions[module] = _functions_in(tree)
        for module, tree in self.trees.items():
            self.imports[module] = _imports(tree, module, package)
        self.classes = {module: {node.name for node in tree.body if isinstance(node, ast.ClassDef)} for module, tree in self.trees.items()}
        # What a class keeps in its attributes: `self.x = Other(...)` (or `... or Other(...)`) makes
        # `self.x.method` a call of Other's method.
        self.attribute_types: dict[tuple[str, str], dict[str, tuple[str, str]]] = defaultdict(dict)
        for module, tree in self.trees.items():
            for node in tree.body:
                if not isinstance(node, ast.ClassDef):
                    continue
                for sub in ast.walk(node):
                    if not isinstance(sub, ast.Assign):
                        continue
                    for target in sub.targets:
                        if isinstance(target, ast.Attribute) and isinstance(target.value, ast.Name) and target.value.id == "self":
                            for call in ast.walk(sub.value):
                                if isinstance(call, ast.Call):
                                    home = self._resolve(module, call.func, "")
                                    if home and home[1] in self.classes.get(home[0], set()):
                                        self.attribute_types[(module, node.name)][target.attr] = home

    def _resolve(self, module: str, sub: ast.AST, owner_class: str) -> tuple[str, str] | None:
        names, modules = self.imports[module]
        local = self.functions[module]
        if isinstance(sub, ast.Name):
            if sub.id in local or sub.id in self.classes[module]:
                return module, sub.id
            if sub.id in names and names[sub.id][0] in self.functions:
                return names[sub.id]
        elif (
            isinstance(sub, ast.Attribute) and isinstance(sub.value, ast.Attribute) and isinstance(sub.value.value, ast.Name)
            and sub.value.value.id == "self" and owner_class
        ):
            kept = self.attribute_types.get((module, owner_class.split(".")[0]), {}).get(sub.value.attr)
            if kept:
                return kept[0], f"{kept[1]}.{sub.attr}"
        elif isinstance(sub, ast.Attribute) and isinstance(sub.value, ast.Name):
            if sub.value.id in {"self", "cls"} and owner_class:
                return module, f"{owner_class}.{sub.attr}"
            if f"{sub.value.id}.{sub.attr}" in local:
                return module, f"{sub.value.id}.{sub.attr}"
            if sub.value.id in modules and modules[sub.value.id] in self.functions:
                return modules[sub.value.id], sub.attr
        return None

    def references(self, module: str, node: ast.AST, owner_class: str = "") -> set[str]:
        """The package's functions a piece of code calls or names; naming a class names its methods."""
        found: set[str] = set()
        for sub in ast.walk(node):
            target = self._resolve(module, sub, owner_class)
            if not target:
                continue
            home, name = target
            if name in self.functions.get(home, {}):
                found.add(f"{self.paths[home]}::{name}")
            elif name in self.classes.get(home, set()):
                found.update(f"{self.paths[home]}::{qualified}" for qualified in self.functions[home] if qualified.startswith(f"{name}."))
        return found

    def call_graph(self) -> dict[str, set[str]]:
        """Per function id ("path::qualname"), the functions of the package it calls or names."""
        graph: dict[str, set[str]] = defaultdict(set)
        for module, functions in self.functions.items():
            for qualname, node in functions.items():
                caller = f"{self.paths[module]}::{qualname}"
                owner_class = qualname.rsplit(".", 1)[0] if "." in qualname else ""
                graph[caller] = self.references(module, node, owner_class) - {caller}
        return graph

    def statement_references(self, path: str, start: int, end: int) -> set[str]:
        """What the module-level statements between two lines name: a marker on a registration names
        the code it registers."""
        module = _module_name(path)
        found: set[str] = set()
        for node in self.trees[module].body:
            if node.lineno <= end and (node.end_lineno or node.lineno) >= start:
                found |= self.references(module, node)
        return found


def unreachable_lines(tree: ast.AST, line: int) -> set[int]:
    """The statements vulture finds unreachable, by their first lines as coverage.py counts statements:
    the one at ``line`` and every one after it in the same block. The compiler drops them, so
    coverage.py lists them neither as run nor as missing."""
    for node in ast.walk(tree):
        for field in ("body", "orelse", "finalbody"):
            block = getattr(node, field, None)
            if not isinstance(block, list):
                continue
            for index, statement in enumerate(block):
                if isinstance(statement, ast.stmt) and statement.lineno == line:
                    return {sub.lineno for later in block[index:] for sub in ast.walk(later) if isinstance(sub, ast.stmt)}
    return {line}


def scope_function(scope: dict, functions: set[str]) -> str | None:
    """The function an @impl scope sits on or inside: a marker covers its whole function."""
    qualname = str(scope.get("qualname") or "")
    while qualname:
        if f"{scope['source']}::{qualname}" in functions:
            return f"{scope['source']}::{qualname}"
        qualname = qualname.rsplit(".", 1)[0] if "." in qualname else ""
    return None


def vulture_findings(root: Path, package: str) -> list[dict]:
    """What vulture finds unused or unreachable in the package, each with its line and confidence."""
    run = subprocess.run(
        ["uvx", "--from", VULTURE, "vulture", f"src/{package}", "--min-confidence", "60"],
        cwd=root, capture_output=True, text=True, check=False,
    )
    rows = []
    pattern = re.compile(r"^(?P<path>[^:]+):(?P<line>\d+): (?P<what>.+?) \((?P<confidence>\d+)% confidence")
    for line in run.stdout.splitlines():
        match = pattern.match(line)
        if not match:
            continue
        what = match.group("what")
        kind = next((word for word in VULTURE_KINDS if what.startswith(f"unused {word}") or what.startswith(word)), None)
        if kind is None:
            continue
        rows.append({"path": match.group("path"), "line": int(match.group("line")), "what": what, "kind": kind,
                     "confidence": int(match.group("confidence"))})
    return rows


def exported_names(root: Path, package: str) -> set[str]:
    """The names the package exports: its `__all__`."""
    tree = ast.parse((root / f"src/{package}/__init__.py").read_text())
    for node in tree.body:
        if isinstance(node, ast.Assign) and any(isinstance(target, ast.Name) and target.id == "__all__" for target in node.targets):
            return {element.value for element in getattr(node.value, "elts", []) if isinstance(element, ast.Constant)}
    return set()


def is_public(qualname: str, exported: set[str]) -> bool:
    """Code a caller of the package reaches: an exported function or class, or a method of an exported
    class that is not private (special methods count as public)."""
    first, *rest = qualname.split(".")
    return first in exported and not any(part.startswith("_") and not part.endswith("__") for part in rest)


def code_map(root: Path, coverage: dict, scopes: list[dict], descendants: dict[str, set[str]],
             test_rows: list[dict], exemptions: dict, package: str = "llm_router") -> dict:
    """Every function of the product with its owners, how it gets them, the tests that run it and
    the causes of the lines no test runs; and the counts a ratchet holds."""
    files = sorted(path for path in coverage["files"] if path.startswith(f"src/{package}/"))
    exported = exported_names(root, package)
    functions: dict[str, dict] = {}
    for path in files:
        data = coverage["files"][path]
        tree = ast.parse((root / path).read_text())
        nodes = _functions_in(tree)
        contexts = data.get("contexts") or {}
        excluded = set(data.get("excluded_lines") or [])
        for qualname, region in (data.get("functions") or {}).items():
            if not qualname or qualname not in nodes:
                continue
            node = nodes[qualname]
            lines = sorted({*region.get("executed_lines", []), *region.get("missing_lines", [])})
            if not lines:
                # A declaration without a statement (a protocol's or an abstract method): nothing to run or own.
                continue
            tests = sorted({
                context.split("|", 1)[0]
                for line in lines for context in contexts.get(str(line), []) if context
            })
            functions[f"{path}::{qualname}"] = {
                "id": f"{path}::{qualname}", "kind": "function", "path": path, "module": _module_name(path), "qualname": qualname,
                "start": node.lineno, "end": node.end_lineno or node.lineno,
                "first": min([node.lineno, *(decorator.lineno for decorator in getattr(node, "decorator_list", []))]),
                "statements": len(lines), "executed": len(region.get("executed_lines", [])),
                "missing_lines": sorted(region.get("missing_lines", [])),
                "excluded_lines": sorted(line for line in excluded if node.lineno <= line <= (node.end_lineno or node.lineno)),
                "tests": tests, "public": is_public(qualname, exported),
            }
    ids = set(functions)
    index = CodeIndex(root, files, package)
    direct: dict[str, set[str]] = defaultdict(set)
    # The markers that name a function, each with the lines it sits on: for ownership it covers the whole function.
    markers: dict[str, list[dict]] = defaultdict(list)
    # A marker on module-level code (a registration) names the functions it registers: they serve
    # its contracts as its helpers do.
    seeded: dict[str, set[str]] = defaultdict(set)
    for scope in scopes:
        if scope.get("error"):
            continue
        marker = {key: scope.get(key) for key in ("impl_id", "kind", "start", "end", "owners")}
        if scope.get("kind") == "class":
            prefix = f"{scope['source']}::{scope['qualname']}."
            for function_id in ids:
                if function_id.startswith(prefix):
                    direct[function_id].update(scope["owners"])
                    markers[function_id].append(marker)
            continue
        function_id = scope_function(scope, ids)
        if function_id:
            direct[function_id].update(scope["owners"])
            markers[function_id].append(marker)
        elif scope.get("source") in files:
            for named in index.statement_references(scope["source"], int(scope["start"]), int(scope["end"])):
                seeded[named].update(scope["owners"])
    graph = index.call_graph()
    callers: dict[str, set[str]] = defaultdict(set)
    for caller, callees in graph.items():
        for callee in callees:
            callers[callee].add(caller)
    inherited: dict[str, set[str]] = defaultdict(set)
    changed = True
    while changed:
        changed = False
        for function_id in ids:
            if direct.get(function_id):
                continue
            owners = set(seeded.get(function_id, set()))
            for caller in callers.get(function_id, set()):
                owners |= direct.get(caller, set()) | inherited.get(caller, set())
            if owners - inherited[function_id]:
                inherited[function_id] |= owners
                changed = True
    findings = vulture_findings(root, package)
    unused_at = {(row["path"], row["line"]): row for row in findings if row["kind"] != "unreachable"}
    # Unreachable code belongs to the innermost function around it; outside every function it is
    # still extraneous, and counted.
    unreachable: dict[str, set[int]] = defaultdict(set)
    loose = []
    for row in findings:
        if row["kind"] != "unreachable" or row["path"] not in index.paths.values():
            continue
        lines = unreachable_lines(index.trees[_module_name(row["path"])], row["line"])
        around = [entry for entry in functions.values() if entry["path"] == row["path"] and entry["start"] <= row["line"] <= entry["end"]]
        if around:
            unreachable[max(around, key=lambda entry: entry["start"])["id"]] |= lines
        else:
            loose.append({"path": row["path"], "lines": sorted(lines), "what": row["what"]})
    verifies = {row["nodeid"]: set(row.get("verifies") or []) for row in test_rows}
    rows = []
    for function_id, entry in sorted(functions.items()):
        owners = sorted(direct.get(function_id, set()))
        via = "direct"
        if not owners:
            owners, via = sorted(inherited.get(function_id, set())), "inherited"
        exemption = exemptions.get(function_id) or {}
        vulture = next((unused_at[(entry["path"], line)] for line in range(entry["first"], entry["start"] + 1) if (entry["path"], line) in unused_at), None)
        unused = bool(vulture and vulture["kind"] in {"function", "method"} and not entry["public"] and not owners)
        # The tests of each owner: those that verify it or a contract derived from it.
        by_owner = {
            owner: {test for test in entry["tests"] if verifies.get(test, set()) & ({owner} | descendants.get(owner, set()))}
            for owner in owners
        }
        owner_tests = sorted(set().union(*by_owner.values())) if by_owner else []
        # A marker claims the function implements each contract it names, so each one's tests must run it; a
        # helper is confirmed when a test of any contract it serves runs it.
        confirmed = all(by_owner.values()) if via == "direct" else bool(owner_tests)
        if unused:
            state = "unused"
        elif owners and via == "direct":
            state = "served" if confirmed else "untested"
        elif owners:
            state = "inherited" if confirmed else "untested"
        elif exemption.get("reason"):
            state = "exempt"
        else:
            state = "unowned"
        causes: dict[str, list[int]] = defaultdict(list)
        for line in entry["missing_lines"]:
            if unused or line in unreachable.get(function_id, set()):
                causes["extraneous"].append(line)
            elif not owners and not exemption.get("reason"):
                causes["no-requirement"].append(line)
            else:
                causes["no-test"].append(line)
        causes["extraneous"].extend(sorted(unreachable.get(function_id, set()) - set(entry["missing_lines"])))
        if entry["excluded_lines"]:
            causes["deactivated"].extend(entry["excluded_lines"])
        rows.append({
            **{key: entry[key] for key in ("id", "kind", "path", "module", "qualname", "start", "end", "statements", "executed", "public")},
            "state": state, "owners": owners, "via": via if owners else "", "callers": sorted(callers.get(function_id, set())),
            "tests": len(entry["tests"]), "owner_tests": len(owner_tests), "confirmed": bool(owners) and confirmed,
            "tests_by_owner": {owner: len(tests) for owner, tests in sorted(by_owner.items())},
            "exemption": exemption, "unused": vulture if unused else None,
            "markers": sorted(markers.get(function_id, []), key=lambda marker: (int(marker["start"]), str(marker["impl_id"]))),
            "causes": {cause: sorted(lines) for cause, lines in causes.items() if lines},
        })
    # A class nothing uses has no function to show it by (an exception never raised, say): it is
    # its own row, unused, unless the package exports it or a marker names it.
    class_owners = {f"{scope['source']}::{scope['qualname']}" for scope in scopes if scope.get("kind") == "class" and not scope.get("error")}
    for (path, line), finding in sorted(unused_at.items()):
        if finding["kind"] != "class":
            continue
        tree = index.trees.get(_module_name(path))
        node = next((node for node in ast.walk(tree) if isinstance(node, ast.ClassDef) and line in {node.lineno, *(d.lineno for d in node.decorator_list)}), None) if tree else None
        if node is None or is_public(node.name, exported) or f"{path}::{node.name}" in class_owners:
            continue
        executed = set(coverage["files"].get(path, {}).get("executed_lines") or [])
        rows.append({
            "id": f"{path}::{node.name}", "kind": "class", "path": path, "module": _module_name(path), "qualname": node.name,
            "start": node.lineno, "end": node.end_lineno or node.lineno, "statements": 1, "executed": int(node.lineno in executed),
            "public": False, "state": "unused", "owners": [], "via": "", "callers": [], "tests": 0, "owner_tests": 0, "confirmed": False, "tests_by_owner": {},
            "exemption": {}, "unused": finding, "causes": {}, "markers": [],
        })
    rows.sort(key=lambda row: str(row["id"]))
    for row in rows:
        row["layers"] = layer_values(row)
    return {"schema": "ternforge-code-map-1", "functions": rows, "counts": map_counts(rows, loose), "loose": loose,
            "vulture": {"tool": VULTURE, "findings": findings}}


def layer_values(row: dict) -> dict[str, str]:
    """What each layer says of one function or class: whom it serves and how, whether its requirement's tests
    run it, whether anything uses it, and the worst cause among the lines no test runs."""
    if row["owners"]:
        owner = "marked" if row["via"] == "direct" else "helper"
    else:
        owner = "exempt" if (row["exemption"] or {}).get("reason") else "none"
    return {
        "owner": owner,
        "run": ("run" if row["confirmed"] else "not-run") if row["owners"] else "na",
        "used": "unused" if row["state"] == "unused" else "used",
        "lines": next((cause for cause in ("extraneous", "no-requirement", "no-test", "deactivated") if row["causes"].get(cause)), "clean"),
    }


def map_counts(rows: list[dict], loose: list[dict]) -> dict:
    """What the map counts: functions and classes, their states, every layer's values, and the lines no test
    runs by cause (unreachable code outside every function included)."""
    lines = {cause: sum(len(row["causes"].get(cause) or []) for row in rows) for cause in CAUSES}
    lines["extraneous"] += sum(len(row["lines"]) for row in loose)
    return {
        "functions": sum(row["kind"] == "function" for row in rows),
        "classes": sum(row["kind"] == "class" for row in rows),
        "states": {state: sum(row["state"] == state for row in rows) for state in STATES},
        "layers": {layer: {value: sum(row["layers"][layer] == value for row in rows) for value in values} for layer, values in LAYERS.items()},
        "lines": lines,
    }


def failing(counts: dict) -> dict[str, int]:
    """How much each layer fails on: functions and classes, and for the lines layer the lines themselves."""
    return {
        layer: sum(counts["lines"][value] for value in values) if layer == "lines" else sum(counts["layers"][layer][value] for value in values)
        for layer, values in FAILING.items()
    }


def load_exemptions(path: Path) -> dict:
    """The functions the owner's delegate decided need no requirement, each with its reason."""
    return json.loads(path.read_text()) if path.is_file() else {}


def ratchet_numbers(counts: dict) -> dict[str, int]:
    """The numbers that may only fall (ADR_0008): functions and classes that serve no requirement, that
    their requirement's tests never run or that nothing uses, and the lines no test runs by cause."""
    return {
        "owner:none": counts["layers"]["owner"]["none"],
        "run:not-run": counts["layers"]["run"]["not-run"],
        "used:unused": counts["layers"]["used"]["unused"],
        **{f"lines:{cause}": counts["lines"][cause] for cause in FAILING["lines"]},
    }


def ratchet(counts: dict, baseline: dict) -> tuple[dict, dict]:
    """The baseline lowered to every number that fell, and the numbers that rose above it, each as
    [held, now]. A rise whose reason the baseline records is accepted: the number is held at its new
    value and the rise moves, with its reason, into the accepted history. A number the baseline does
    not hold yet starts at its value now."""
    now = ratchet_numbers(counts)
    held = dict(baseline.get("numbers") or {})
    reasons = dict(baseline.get("reasons") or {})
    accepted = list(baseline.get("accepted") or [])
    numbers, rises = {}, {}
    for key, value in now.items():
        if key in held and value > held[key]:
            reason = str(reasons.pop(key, "") or "").strip()
            if reason:
                accepted.append({"number": key, "from": held[key], "to": value, "reason": reason})
                numbers[key] = value
            else:
                rises[key] = [held[key], value]
                numbers[key] = held[key]
        else:
            numbers[key] = min(held.get(key, value), value)
    return {**baseline, "schema": "ternforge-code-map-baseline-1", "numbers": numbers, "reasons": reasons, "accepted": accepted}, rises
