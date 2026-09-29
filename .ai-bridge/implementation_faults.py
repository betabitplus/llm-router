"""Implementation fault classes for every contract with an attributable @impl scope.

The engine is pytest-gremlins with the project's extension (``pytest_plugins``): its
native operator families and the extension's statement, body and Python operators are mapped
to the Test Plan's Implementation fault classes and run against the contract's own
passing tests. This module owns what the engine cannot know: which source lines belong
to which contract (from the graph's IMPL needs), which tests may challenge them, which
arid-code rules apply to the contract, and how a retained engine report projects onto
fault classes. It never infers ownership from names. A line several contracts claim is
challenged for each of them with that contract's own tests (2026-09-28): a claim is tested
where it is made, and a survivor is judged for the contract whose tests let it through.
"""

from __future__ import annotations

import ast
import hashlib
import io
import json
import os
import re
import shutil
import subprocess
import time
import tokenize
from collections import defaultdict
from datetime import UTC, datetime
from pathlib import Path

SCHEMA = "ternforge-implementation-fault-campaign-2"
GREMLINS_VERSION = "1.9.0"
OPERATORS = (
    "comparison", "boundary", "arithmetic", "boolean", "return", "statement", "body",
    "argument", "condition", "conditional", "negation", "container", "conversion", "method", "attribute",
)
CLASS_BY_OPERATOR = {
    "comparison": "impl.comparison",
    "boundary": "impl.boundary",
    "arithmetic": "impl.arithmetic",
    "boolean": "impl.control-flow",
    "return": "impl.control-flow",
    "statement": "impl.effect",
    "body": "impl.effect",
    # Python's own faults (the extension's PyTation operators) lose a value's effect or read the
    # wrong one; the operators that change a condition change a branch.
    "argument": "impl.effect",
    "conversion": "impl.effect",
    "method": "impl.effect",
    "container": "impl.effect",
    "attribute": "impl.effect",
    "condition": "impl.control-flow",
    "conditional": "impl.control-flow",
    "negation": "impl.control-flow",
}
CLASSES = ("impl.comparison", "impl.boundary", "impl.arithmetic", "impl.control-flow", "impl.effect")
CLASS_NOUNS = {
    "impl.comparison": "comparison",
    "impl.boundary": "boundary",
    "impl.arithmetic": "arithmetic",
    "impl.control-flow": "branch/return",
    "impl.effect": "effect",
}
KILLED = {"zapped", "timeout"}
# A mutant whose run ends in a collection/import/internal error is invalid (as in
# Stryker's RuntimeError/CompileError): neither caught nor missed, and reported apart.
INVALID = {"error"}
# What one mutant came to, in the Test Plan's words: caught, survived (its line runs and
# every test passes), not reached (no test of the contract runs its line), invalid, suppressed.
OUTCOMES = ("caught", "survived", "notreached", "invalid", "suppressed")
PRODUCERS = ("PRODUCER_PYTEST_GREMLINS", "PRODUCER_IMPLEMENTATION_FAULT_ADAPTER")


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


# --- fingerprints by meaning --------------------------------------------------------
# A fingerprint answers one question: could a retained result differ now? Bytes answer too
# often: a comment, a docstring or a reformatting changes them and changes nothing a run does.


# A fingerprint stays with its file until the file changes: a refresh asks for the same modules'
# fingerprints hundreds of times, and each would parse them again.
_DIGESTS: dict[tuple[str, str, int, int], str] = {}


def _remembered(kind: str, path: Path, compute) -> str | None:
    """The fingerprint ``compute`` gives a file, kept by its path, size and modification time."""
    try:
        stat = path.stat()
    except OSError:
        return None
    if not path.is_file():
        return None
    key = (kind, str(path.resolve()), stat.st_size, stat.st_mtime_ns)
    if key not in _DIGESTS:
        _DIGESTS[key] = compute(path)
    return _DIGESTS[key]


def code_digest(path: Path) -> str | None:
    """What a tool's module does, not how it reads: its syntax tree without comments,
    docstrings, positions or formatting. A module that does not parse counts by its bytes."""
    return _remembered("code", path, _code_digest)


def _code_digest(path: Path) -> str:
    source = path.read_bytes()
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return sha256_bytes(source)
    for node in ast.walk(tree):
        if isinstance(node, (ast.Module, ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)):
            first = node.body[0] if node.body else None
            if isinstance(first, ast.Expr) and isinstance(first.value, ast.Constant) and isinstance(first.value.value, str):
                node.body = node.body[1:] or [ast.Pass()]
    return sha256_bytes(ast.dump(tree, include_attributes=False).encode())


# The engine reads these comments (ternforge_mutation.PRAGMA); every other comment is prose.
MUTATION_DIRECTIVE = re.compile(r"#\s*mutation:")


def source_digest(path: Path) -> str | None:
    """What the engine mutates and where: a module's tokens at their positions and its
    ``# mutation:`` pragmas, without other comments. A comment edited in place moves no
    mutant and changes nothing; a line added or removed moves every mutant below it and
    does. A module that does not tokenize counts by its bytes."""
    return _remembered("source", path, _source_digest)


def _source_digest(path: Path) -> str:
    source = path.read_bytes()
    kept = []
    try:
        for token in tokenize.tokenize(io.BytesIO(source).readline):
            if token.type == tokenize.COMMENT:
                if MUTATION_DIRECTIVE.match(token.string):
                    kept.append((token.type, token.string, token.start))
            elif token.type in {tokenize.NL, tokenize.NEWLINE}:
                # A newline's column follows the comment before it, so only its place in the
                # token stream counts.
                kept.append((token.type,))
            else:
                kept.append((token.type, token.string, token.start, token.end))
    except (tokenize.TokenError, SyntaxError):
        return sha256_bytes(source)
    return sha256_bytes(repr(kept).encode())


def stable_json(value) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"))


# --- scope attribution -------------------------------------------------------------


def annotated_node(tree: ast.AST, lines: list[str], comment_line: int):
    """Return the statement an @impl comment annotates, or None.

    The annotation is the comment block directly above the statement; decorators may
    sit above or below it.
    """
    first = comment_line + 1
    while first <= len(lines) and (
        not lines[first - 1].strip() or lines[first - 1].lstrip().startswith("#")
    ):
        first += 1
    best = None
    for node in ast.walk(tree):
        if not isinstance(node, ast.stmt):
            continue
        starts = {node.lineno, *[d.lineno for d in getattr(node, "decorator_list", [])]}
        if first in starts and (
            best is None
            or (node.end_lineno or node.lineno) - node.lineno
            > (best.end_lineno or best.lineno) - best.lineno
        ):
            best = node
    return best


def scope_kind_and_name(tree: ast.AST, node: ast.stmt, start: int) -> tuple[str, str]:
    parents = {}
    for parent in ast.walk(tree):
        for child in ast.iter_child_nodes(parent):
            parents[child] = parent
    chain = []
    current = node
    while current in parents:
        current = parents[current]
        if isinstance(current, (ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)):
            chain.append(current.name)
    own = getattr(node, "name", None) or f"L{start}"
    qualname = ".".join([*reversed(chain), own])
    if isinstance(node, ast.ClassDef):
        return "class", qualname
    if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
        return ("method" if chain else "function"), qualname
    return "statement", qualname


def resolve_impl_scopes(root: Path, needs: dict) -> list[dict]:
    scopes = []
    parsed: dict[str, tuple[list[str], ast.AST]] = {}
    for impl_id, need in sorted(needs.items()):
        if need.get("type") != "impl":
            continue
        owners = sorted(
            {str(ref).split("[", 1)[0] for ref in need.get("implements") or []}
        )
        row = {"impl_id": impl_id, "title": need.get("title") or impl_id, "owners": owners}
        match = re.fullmatch(r"(?P<path>[^#]+)#L(?P<line>\d+)", str(need.get("source_url") or ""))
        if not match:
            scopes.append({**row, "error": "the IMPL need has no source line"})
            continue
        path = match.group("path")
        if path not in parsed:
            text = (root / path).read_text()
            parsed[path] = (text.splitlines(), ast.parse(text))
        lines, tree = parsed[path]
        node = annotated_node(tree, lines, int(match.group("line")))
        if node is None:
            scopes.append({**row, "source": path, "error": "no statement follows the @impl annotation"})
            continue
        start = min([node.lineno, *[d.lineno for d in getattr(node, "decorator_list", [])]])
        end = int(node.end_lineno or node.lineno)
        kind, qualname = scope_kind_and_name(tree, node, start)
        scopes.append(
            {**row, "source": path, "kind": kind, "qualname": qualname, "start": start, "end": end}
        )
    return scopes


def descendants_map(needs: dict) -> dict[str, set[str]]:
    parents: dict[str, set[str]] = defaultdict(set)
    for need_id, need in needs.items():
        if need.get("type") in {"req", "treq"}:
            for parent in need.get("derives") or []:
                parents[need_id].add(str(parent).split("[", 1)[0])
    result: dict[str, set[str]] = defaultdict(set)
    for child in list(parents):
        pending = list(parents[child])
        seen = set()
        while pending:
            ancestor = pending.pop()
            if ancestor in seen:
                continue
            seen.add(ancestor)
            result[ancestor].add(child)
            pending.extend(parents.get(ancestor) or [])
    return result


def line_owners(scopes: list[dict]) -> dict[tuple[str, int], set[str]]:
    owners: dict[tuple[str, int], set[str]] = defaultdict(set)
    for scope in scopes:
        if scope.get("error"):
            continue
        for line in range(int(scope["start"]), int(scope["end"]) + 1):
            owners[(scope["source"], line)].update(scope["owners"])
    return owners


def contract_plan(
    contract_id: str,
    scopes: list[dict],
    owners_by_line: dict[tuple[str, int], set[str]],
    descendants: dict[str, set[str]],
    test_rows: list[dict],
) -> dict:
    """What a campaign may challenge for one contract, and why not when it cannot."""
    own_scopes = [s for s in scopes if contract_id in s["owners"] and not s.get("error")]
    family = {contract_id, *descendants.get(contract_id, set())}
    attributable: dict[str, list[int]] = defaultdict(list)
    shared_with: set[str] = set()
    for scope in own_scopes:
        for line in range(int(scope["start"]), int(scope["end"]) + 1):
            # Every claimant challenges the line with its own tests; the others that claim it
            # are recorded, not excluded.
            shared_with.update(owners_by_line[(scope["source"], line)] - family)
            attributable[scope["source"]].append(line)
    tests = sorted(
        {
            row["nodeid"]
            for row in test_rows
            if row.get("result") == "passed" and family & set(row.get("verifies") or [])
        }
    )
    not_passing = sorted(
        {
            row["nodeid"]
            for row in test_rows
            if row.get("result") != "passed" and family & set(row.get("verifies") or [])
        }
    )
    seconds = {row["nodeid"]: row.get("seconds") for row in test_rows if row.get("result") == "passed"}
    measured = [float(value) for nodeid in tests if (value := seconds.get(nodeid)) is not None]
    plan = {
        "contract_id": contract_id,
        "scopes": [
            {k: s[k] for k in ("impl_id", "source", "kind", "qualname", "start", "end", "owners")}
            for s in own_scopes
        ],
        "attributable_lines": {path: sorted(set(lines)) for path, lines in sorted(attributable.items())},
        "shared_with": sorted(shared_with),
        "tests": tests,
        "tests_not_passing": not_passing,
        "files": sorted(attributable),
        # What its tests took in the retained run: the base of a mutant's time limit (time_limits).
        "baseline_seconds": round(sum(measured), 3) if tests and len(measured) == len(tests) else None,
    }
    if not own_scopes:
        plan["blocked"] = "no_impl_scope"
    elif not attributable:
        plan["blocked"] = "shared_scope"
    elif not tests:
        plan["blocked"] = "no_passing_tests"
    return plan


def blocked_basis(plan: dict) -> str:
    reason = plan.get("blocked")
    if reason == "no_impl_scope":
        return "No @impl annotation implements this contract, so implementation faults have no target."
    if reason == "shared_scope":
        others = list(plan.get("shared_with") or [])
        named = ", ".join(others[:2]) + (f" and {len(others) - 2} more" if len(others) > 2 else "")
        scopes = ", ".join(sorted({scope["qualname"] for scope in plan.get("scopes") or []}))
        return (
            f"Its code ({scopes}) is also claimed by {named or 'other contracts'}, so a fault there "
            "cannot be pinned on this contract alone. Give it its own, narrower @impl scope."
        )
    if reason == "no_passing_tests":
        return "No passing test verifies this contract or its derived contracts, so nothing can challenge its code."
    return str(reason or "")


# --- projection --------------------------------------------------------------------


def mutant_outcome(result: dict) -> str:
    """One engine result in the Test Plan's words."""
    status = str(result.get("status") or "error")
    if status in KILLED:
        return "caught"
    if status == "pardoned":
        return "suppressed"
    if status in INVALID:
        return "invalid"
    # Reach is the coverage fact the extension records per mutant; without it (an
    # engine run without coverage) a surviving mutant counts as reached, never as better.
    return "notreached" if result.get("covered") is False else "survived"


def relative_source(root: Path, file_path: object) -> str:
    raw_path = Path(str(file_path or ""))
    try:
        return str(raw_path.resolve().relative_to(root.resolve()))
    except ValueError:
        return str(raw_path)


def contract_mutants(plan: dict, report: dict, root: Path) -> list[dict]:
    """The report's mutants on the contract's attributable lines, one row each."""
    allowed = {
        (path, line)
        for path, lines in (plan.get("attributable_lines") or {}).items()
        for line in lines
    }
    rows = []
    for result in report.get("results") or []:
        relative = relative_source(root, result.get("file_path"))
        line = int(result.get("line_number") or -1)
        fault_class = CLASS_BY_OPERATOR.get(str(result.get("operator") or ""))
        if fault_class is None or (relative, line) not in allowed:
            continue
        rows.append(
            {
                "id": str(result.get("gremlin_id") or ""),
                "fingerprint": str(result.get("fingerprint") or result.get("gremlin_id") or ""),
                "class": fault_class,
                "operator": str(result.get("operator")),
                "description": str(result.get("description") or ""),
                "source": relative,
                "line": line,
                "qualname": str(result.get("qualname") or ""),
                "location": result.get("location"),
                "original": str(result.get("original") or ""),
                "replacement": str(result.get("replacement") or ""),
                "status": str(result.get("status") or "error"),
                "outcome": mutant_outcome(result),
                "covered": result.get("covered"),
                "suppression": result.get("suppression"),
                "run_skipped": result.get("run_skipped"),
                "selected_tests": len(result.get("selected_tests") or []),
            }
        )
    return rows


def not_planted_mutants(plan: dict, report: dict, root: Path) -> list[dict]:
    """Mutants the arid-code rules kept out of the contract's attributable lines."""
    allowed = {
        (path, line)
        for path, lines in (plan.get("attributable_lines") or {}).items()
        for line in lines
    }
    rows = []
    for item in (report.get("ternforge") or {}).get("not_planted") or []:
        relative = relative_source(root, item.get("file_path"))
        fault_class = CLASS_BY_OPERATOR.get(str(item.get("operator") or ""))
        if fault_class is None or (relative, int(item.get("line_number") or -1)) not in allowed:
            continue
        rows.append({**item, "source": relative, "class": fault_class})
    return rows


def suppress_by_verdict(rows: list[dict], verdicts: dict[str, dict] | None) -> list[dict]:
    """Mutant rows with every survivor or unreached mutant a current verdict judged equivalent or
    irrelevant (ADR_0006) suppressed, with the verdict, its reason and who gave it."""
    for row in rows:
        verdict = (verdicts or {}).get(row["fingerprint"])
        if verdict and row["outcome"] in {"survived", "notreached"}:
            row["outcome"] = "suppressed"
            row["suppression"] = {"verdict": verdict.get("verdict"), "reason": verdict.get("reason"), "by": verdict.get("by"), "reviewed_by": verdict.get("reviewed_by")}
    return rows


def project_classes(plan: dict, report: dict, root: Path, verdicts: dict[str, dict] | None = None) -> dict[str, dict]:
    """Project one retained engine report onto the contract's Implementation classes.

    A class is caught only when it has at least one valid, unsuppressed mutant and
    every such mutant is caught; a mutant no test of the contract reaches is not
    caught. Invalid and suppressed mutants are counted apart and never count as
    caught; mutants in arid code were never planted and are counted by rule.
    ``verdicts`` names, by fingerprint, surviving mutants a current verdict judged
    equivalent or irrelevant (ADR_0006): they are suppressed, with the verdict.
    """
    rows = suppress_by_verdict(contract_mutants(plan, report, root), verdicts)
    arid = not_planted_mutants(plan, report, root)
    classes = {}
    for fault_class in CLASSES:
        class_rows = [row for row in rows if row["class"] == fault_class]
        counts = {outcome: sum(row["outcome"] == outcome for row in class_rows) for outcome in OUTCOMES}
        judged = counts["caught"] + counts["survived"] + counts["notreached"]
        reached = counts["caught"] + counts["survived"]
        not_planted: dict[str, int] = defaultdict(int)
        for item in arid:
            if item["class"] == fault_class:
                not_planted[str(item.get("rule"))] += 1
        noun = CLASS_NOUNS[fault_class]

        def faults(count: int) -> str:
            return f"{count} {noun} fault" + ("" if count == 1 else "s")

        if not judged and counts["suppressed"]:
            basis = f"Every {noun} fault ({counts['suppressed']}) is suppressed, so none is judged."
        elif not judged and counts["invalid"]:
            basis = f"Every {noun} fault ({counts['invalid']}) broke test collection, so none could be judged."
        elif not judged:
            basis = f"No {noun} fault site in the attributable code, so this class cannot be challenged here."
        elif not reached:
            basis = f"The contract's tests never reach its {faults(judged)}."
        elif counts["caught"] == judged:
            basis = (
                f"The contract's tests catch its only {noun} fault."
                if judged == 1
                else f"The contract's tests catch all {faults(judged)}."
            )
        else:
            parts = []
            if counts["survived"]:
                parts.append(f"{counts['survived']} survive")
            if counts["notreached"]:
                parts.append(f"{counts['notreached']} are never reached")
            basis = f"The contract's tests catch {counts['caught']} of {faults(judged)}; " + " and ".join(parts) + "."
        extra = []
        if judged and counts["suppressed"]:
            extra.append(f"{counts['suppressed']} more are suppressed")
        if judged and counts["invalid"]:
            extra.append(f"{counts['invalid']} more broke test collection")
        if extra:
            basis += " " + "; ".join(extra).capitalize() + "."
        classes[fault_class] = {
            "exercised": bool(reached),
            "detected": bool(judged) and counts["caught"] == judged,
            "generated": len(class_rows),
            "judged": judged,
            "reached": reached,
            "killed": counts["caught"],
            "caught": counts["caught"],
            "survived": counts["survived"] + counts["notreached"],
            "survived_reached": counts["survived"],
            "unreached": counts["notreached"],
            "pardoned": counts["suppressed"],
            "suppressed": counts["suppressed"],
            "suppressed_by_verdict": sum(1 for row in class_rows if row["outcome"] == "suppressed" and (row.get("suppression") or {}).get("verdict")),
            "invalid": counts["invalid"],
            "not_planted": dict(sorted(not_planted.items())),
            "survivors": [
                {k: row[k] for k in ("source", "line", "operator", "description", "fingerprint", "qualname")}
                | {"reached": row["outcome"] == "survived"}
                for row in sorted(
                    (row for row in class_rows if row["outcome"] in {"survived", "notreached"}),
                    key=lambda row: (row["source"], row["line"], row["id"]),
                )
            ][:25],
            "basis": basis,
        }
    return classes


def blocked_classes(basis: str) -> dict[str, dict]:
    return {
        fault_class: {"exercised": False, "detected": False, "basis": basis}
        for fault_class in CLASSES
    }


# --- inputs and freshness ----------------------------------------------------------

# Anything that can change any contract's result is a shared input: test support, test data,
# the examples and the dependencies. Product code counts per contract, as PIT and Stryker count
# it: a result stays current while the files that hold its mutants (contract_inputs) and its own
# tests are unchanged. A change elsewhere in the product that alters what that code calls is the
# risk they accept too; the pull-request diff mutates the changed lines themselves, and a full run
# (--full) starts every contract over.
SHARED_INPUT_SCOPE = (
    "tests/llm_router/data/**/*",
    "examples/**/*.py",
)
SHARED_EXPLICIT_INPUTS = ("pyproject.toml", "uv.lock")


def _files(root: Path, pattern: str) -> set[Path]:
    return {
        path
        for path in root.glob(pattern)
        if path.is_file() and "__pycache__" not in path.parts
    }


def input_digest(path: Path) -> str | None:
    """A Python input by what the engine runs (``source_digest``), any other file by its bytes."""
    if path.suffix == ".py":
        return source_digest(path)
    return sha256_bytes(path.read_bytes()) if path.is_file() else None


def digest_map(root: Path, paths: set[str]) -> dict[str, str | None]:
    return {relative: input_digest(root / relative) for relative in sorted(paths)}


def shared_inputs(root: Path) -> dict[str, str | None]:
    paths: set[Path] = set()
    for pattern in SHARED_INPUT_SCOPE:
        paths |= _files(root, pattern)
    # Test support: every conftest, fixture and helper module (anything that is not a
    # test module) can be imported by any test.
    paths |= {path for path in _files(root, "tests/**/*.py") if not path.name.startswith("test_")}
    for relative in SHARED_EXPLICIT_INPUTS:
        if (root / relative).is_file():
            paths.add(root / relative)
    return digest_map(root, {str(path.relative_to(root)) for path in paths})


def _imported_test_modules(root: Path, test_file: str) -> set[str]:
    """Test modules a test module imports (for example shared step definitions)."""
    found: set[str] = set()
    pending = [test_file]
    while pending:
        current = pending.pop()
        if current in found or not (root / current).is_file():
            continue
        found.add(current)
        tree = ast.parse((root / current).read_text())
        package = Path(current).parent
        for node in ast.walk(tree):
            names: list[str] = []
            if isinstance(node, ast.Import):
                names = [alias.name for alias in node.names]
            elif isinstance(node, ast.ImportFrom):
                if node.level:
                    base = package
                    for _ in range(node.level - 1):
                        base = base.parent
                    prefix = ".".join(base.parts)
                    names = [f"{prefix}.{node.module}" if node.module else prefix]
                    names += [f"{names[0]}.{alias.name}" for alias in node.names]
                elif node.module:
                    names = [node.module, *[f"{node.module}.{alias.name}" for alias in node.names]]
            for name in names:
                candidate = Path(*name.split(".")).with_suffix(".py")
                if candidate.parts and candidate.parts[0] == "tests" and candidate.name.startswith("test_"):
                    pending.append(str(candidate))
    return found


def contract_inputs(root: Path, plan: dict, test_rows: list[dict]) -> dict[str, str | None]:
    """The contract's own inputs: the product files that hold its mutants, and its test modules,
    their Gherkin and their cassettes."""
    rows = {row["nodeid"]: row for row in test_rows}
    paths: set[str] = set(plan.get("files") or [])
    for nodeid in plan.get("tests") or []:
        test_file = nodeid.split("::", 1)[0]
        for module in _imported_test_modules(root, test_file):
            paths.add(module)
            cassettes = Path(module).parent / "cassettes" / Path(module).stem
            paths |= {str(path.relative_to(root)) for path in _files(root, f"{cassettes}/**/*")}
        feature = str((rows.get(nodeid) or {}).get("gherkin_feature") or "").strip()
        if feature:
            paths.add(feature if feature.startswith("features/") else f"features/{feature}")
    return digest_map(root, paths)


def plugin_sha256() -> str | None:
    """One digest over what every module of the engine extension does (``code_digest``)."""
    modules = sorted(PLUGIN_DIR.glob("*.py"))
    if not modules:
        return None
    return sha256_bytes(b"".join(module.name.encode() + b"\0" + str(code_digest(module)).encode() for module in modules))


# A mutant's time limit follows its tests, as PIT's does (factor × their time + a constant). The
# contract's tests took `baseline_seconds` in the retained run; a mutant gets 1.25 times that
# plus 10 s for pytest's own start, and a run that outlasts it runs once more with twice as much
# before the timeout counts as caught. Without a measured baseline the fixed limits stay.
TIME_LIMIT_FACTOR = 1.25
TIME_LIMIT_CONSTANT_SECONDS = 10.0
TIME_LIMIT_CONFIRM_FACTOR = 2.0
TIME_LIMITS_WITHOUT_BASELINE = (30.0, 300.0)
# The engine extension reads them (gremlins_full_pytest.TIMEOUT_ENV and CONFIRM_TIMEOUT_ENV).
TIMEOUT_ENV = "TERNFORGE_GREMLIN_TIMEOUT"
CONFIRM_TIMEOUT_ENV = "TERNFORGE_GREMLIN_CONFIRM_TIMEOUT"


def time_limits(baseline_seconds: float | None) -> tuple[float, float]:
    """The first and the confirming time limit of a mutant's tests, in seconds."""
    if baseline_seconds is None:
        return TIME_LIMITS_WITHOUT_BASELINE
    limit = round(TIME_LIMIT_FACTOR * max(0.0, float(baseline_seconds)) + TIME_LIMIT_CONSTANT_SECONDS, 1)
    return limit, round(TIME_LIMIT_CONFIRM_FACTOR * limit, 1)


def engine_configuration() -> dict:
    return {
        "engine": GREMLINS_VERSION,
        "mode": "full pytest per mutant",
        "scope": "attributable @impl lines only",
        "operators": list(OPERATORS),
        "plugin_sha256": plugin_sha256(),
        "hermetic_options": list(HERMETIC_OPTIONS),
        "time_limits": {
            "factor": TIME_LIMIT_FACTOR,
            "constant_seconds": TIME_LIMIT_CONSTANT_SECONDS,
            "confirm_factor": TIME_LIMIT_CONFIRM_FACTOR,
            "without_baseline": list(TIME_LIMITS_WITHOUT_BASELINE),
        },
    }


def plan_key(plan: dict) -> dict:
    return {
        "attributable_lines": plan.get("attributable_lines"),
        "tests": plan.get("tests"),
        "arid_rules": plan.get("arid_rules"),
    }


def entry_state(entry: dict, plan: dict, shared_sha256: str, own_inputs: dict) -> tuple[str, str]:
    """Is a retained campaign result still the result the engine would produce now?"""
    if entry.get("engine") != engine_configuration():
        return "stale", "the mutation engine configuration changed"
    if entry.get("plan_key") != plan_key(plan):
        return "stale", "the contract's code scope or its passing tests changed"
    if entry.get("shared_inputs_sha256") != shared_sha256:
        return "stale", "product code, shared test support or dependencies changed"
    recorded = entry.get("inputs") or {}
    changed = sorted(
        path for path in set(recorded) | set(own_inputs) if recorded.get(path) != own_inputs.get(path)
    )
    if changed:
        more = f" (+{len(changed) - 3} more)" if len(changed) > 3 else ""
        return "stale", "its tests changed: " + ", ".join(changed[:3]) + more
    return "current", ""


# --- engine run --------------------------------------------------------------------


PLUGIN_DIR = Path(__file__).resolve().parent / "pytest_plugins"
HERMETIC_OPTIONS = (
    "--record-mode=none",
    "--block-network",
    r"--allowed-hosts=localhost,127\.0\.0\.1",
)


def engine_env(
    scratch: Path,
    *,
    hermetic: bool = True,
    scope: dict[str, list[int]] | None = None,
    arid_rules: list[str] | None = None,
    skip_uncovered: bool = False,
    limits: tuple[float, float] | None = None,
) -> dict[str, str]:
    """Environment shared by the outer engine run and every per-mutant pytest run.

    PYTEST_ADDOPTS reaches the per-mutant subprocesses too, so each of them runs
    with full pytest (lightweight runner disabled), fixed order, and, for the
    project suite, the same hermetic network rules as the retained run. A scope
    keeps only the mutants on those source lines; the arid rules are the ones that
    apply to the contract; skipping uncovered mutants is the pull-request diff.
    """
    scratch.mkdir(parents=True, exist_ok=True)
    scope_env: dict[str, str] = {}
    if scope is not None:
        scope_file = scratch / f"gremlin-scope-{sha256_bytes(stable_json(scope).encode())[:16]}.json"
        scope_file.write_text(stable_json(scope))
        scope_env["TERNFORGE_GREMLIN_SCOPE"] = str(scope_file)
    if arid_rules is not None:
        policy = {"arid_rules": sorted(arid_rules)}
        policy_file = scratch / f"mutation-policy-{sha256_bytes(stable_json(policy).encode())[:16]}.json"
        policy_file.write_text(stable_json(policy))
        scope_env["TERNFORGE_MUTATION_POLICY"] = str(policy_file)
    if skip_uncovered:
        scope_env["TERNFORGE_GREMLIN_SKIP_UNCOVERED"] = "1"
    if limits is not None:
        scope_env[TIMEOUT_ENV], scope_env[CONFIRM_TIMEOUT_ENV] = (str(seconds) for seconds in limits)
    addopts = ["-p", "no:randomly", "-p", "no:cacheprovider", "-p", "gremlins_full_pytest"]
    if hermetic:
        addopts.extend(HERMETIC_OPTIONS)
    python_path = [str(PLUGIN_DIR), *filter(None, [os.environ.get("PYTHONPATH")])]
    return {
        **os.environ,
        "PYTHONPATH": os.pathsep.join(python_path),
        "PYTEST_ADDOPTS": " ".join(addopts),
        "TERNFORGE_EVIDENCE_RUN_INPUTS": str(scratch / "engine-run-inputs.json"),
        "OBJC_DISABLE_INITIALIZE_FORK_SAFETY": "YES",
        "PYTHONDONTWRITEBYTECODE": "1",
        **scope_env,
    }


def engine_command(root: Path, tests: list[str], targets: list[str], *, project: Path | None = None, config: str | None = None) -> list[str]:
    command = [shutil.which("uv") or "uv", "run"]
    if project is not None:
        command.extend(["--project", str(project)])
    command.extend(["--with", f"pytest-gremlins=={GREMLINS_VERSION}", "pytest", "-q"])
    if config:
        command.extend(["-c", config])
    return [
        *command,
        *tests,
        "--gremlins",
        f"--gremlin-targets={','.join(targets)}",
        "--gremlin-report=json",
        f"--gremlin-operators={','.join(OPERATORS)}",
    ]


def run_engine(
    root: Path,
    plan: dict,
    raw_path: Path,
    timeout: int = 5400,
    *,
    scope: dict[str, list[int]] | None = None,
    skip_uncovered: bool = False,
    project: Path | None = None,
    scratch: Path | None = None,
) -> dict:
    """Run pytest-gremlins for one contract in place and retain its JSON report.

    The scope defaults to the contract's attributable lines; the pull-request diff
    narrows it to the changed ones and skips the mutants no test covers. A run in a
    copy of the working tree names the project whose environment it uses and a
    scratch folder of its own.
    """
    report_dir = root / "coverage/gremlins"
    coverage_dir_existed = (root / "coverage").exists()
    env = engine_env(
        scratch or Path(os.environ.get("TMPDIR", "/tmp")) / "ternforge-probe-scratch",
        scope=scope if scope is not None else plan["attributable_lines"],
        arid_rules=plan.get("arid_rules"),
        skip_uncovered=skip_uncovered,
        limits=time_limits(plan.get("baseline_seconds")),
    )
    files = sorted(scope) if scope is not None else plan["files"]
    command = [*engine_command(root, plan["tests"], files, project=project), "--no-cov"]
    started = time.monotonic()
    shutil.rmtree(report_dir, ignore_errors=True)
    try:
        completed = subprocess.run(
            command,
            cwd=root,
            env=env,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            timeout=timeout,
        )
        output = completed.stdout or ""
        returncode = completed.returncode
    except subprocess.TimeoutExpired as exc:
        output = str(exc.stdout or "")
        returncode = None
    report_file = report_dir / "gremlins.json"
    sidecar_file = report_dir / "ternforge-extension.json"
    sidecar = json.loads(sidecar_file.read_text()) if sidecar_file.exists() else {}
    retained = False
    if report_file.exists():
        raw_path.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(str(report_file), raw_path)
        retained = True
    elif returncode == 0 and "No gremlins found in source code" in output:
        # The engine ran and found no mutation site in the targets: retain that
        # outcome as an empty report instead of treating it as an engine failure.
        raw_path.parent.mkdir(parents=True, exist_ok=True)
        raw_path.write_text(
            json.dumps(
                {
                    "results": [],
                    "summary": {"total": 0},
                    "note": "no mutation site in the targets",
                    # What the extension decided before the engine found nothing to run.
                    **({"ternforge": sidecar["ternforge"]} if sidecar.get("ternforge") else {}),
                },
                indent=2,
                sort_keys=True,
            )
            + "\n"
        )
        retained = True
    shutil.rmtree(report_dir, ignore_errors=True)
    if not coverage_dir_existed:
        shutil.rmtree(root / "coverage", ignore_errors=True)
    (root / ".coveragerc.gremlins").unlink(missing_ok=True)
    return {
        "returncode": returncode,
        "report_retained": retained,
        "duration_seconds": round(time.monotonic() - started, 3),
        "output_tail": "\n".join(output.splitlines()[-25:]),
        "command": command,
    }


def engine_workers() -> int:
    """How many contracts a campaign mutates at once: TERNFORGE_MUTATION_WORKERS, else the
    machine's cores less one, at most eight. Each contract still runs its mutants one by one."""
    configured = os.environ.get("TERNFORGE_MUTATION_WORKERS")
    if configured:
        return max(1, int(configured))
    return max(1, min(8, (os.cpu_count() or 2) - 1))


def working_tree_copy(root: Path, destination: Path) -> Path:
    """A copy of the working tree as the tests see it: the files git tracks or would track,
    changes included, or the whole folder outside a repository."""
    listed = subprocess.run(["git", "ls-files", "-co", "--exclude-standard", "-z"], cwd=root, capture_output=True, check=False)
    if listed.returncode != 0:
        shutil.copytree(root, destination, ignore=shutil.ignore_patterns("__pycache__", ".pytest_cache", "coverage"))
        return destination
    for name in filter(None, listed.stdout.decode().split("\0")):
        source = root / name
        if source.is_file():
            target = destination / name
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, target)
    return destination


def run_engine_isolated(root: Path, copy_root: Path, plan: dict, raw_path: Path, **options: object) -> dict:
    """Run the engine for one contract in a copy of the working tree, so several contracts can
    run at once, and retain its report with the working tree's own paths. The copy uses the
    environment of ``project``, the working tree's own unless told otherwise."""
    project = Path(str(options.pop("project", root)))
    run = run_engine(copy_root, plan, raw_path, project=project, scratch=copy_root / ".ternforge-scratch", **options)
    if run["report_retained"]:
        text = raw_path.read_text()
        for prefix in sorted({str(copy_root.resolve()), str(copy_root)}, key=len, reverse=True):
            text = text.replace(prefix, str(root.resolve()))
        raw_path.write_text(text)
    return run


def utc_now() -> str:
    return datetime.now(UTC).isoformat().replace("+00:00", "Z")
