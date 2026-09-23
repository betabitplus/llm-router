"""Implementation fault classes for every contract with an attributable @impl scope.

The engine is pytest-gremlins: its native operator families are mapped to the test
plan's Implementation fault classes and run against the contract's own passing tests.
This module owns what the engine cannot know: which source lines belong to which
contract (from the graph's IMPL needs), which tests may challenge them, and how a
retained engine report projects onto fault classes. It never infers ownership from
names; a line shared with a contract that does not derive from the challenged one is
not attributable and is reported as such.
"""

from __future__ import annotations

import ast
import hashlib
import json
import os
import re
import shutil
import subprocess
import time
from collections import defaultdict
from datetime import UTC, datetime
from pathlib import Path

SCHEMA = "ternforge-implementation-fault-campaign-1"
GREMLINS_VERSION = "1.9.0"
OPERATORS = ("comparison", "boundary", "boolean", "return")
CLASS_BY_OPERATOR = {
    "comparison": "impl.comparison",
    "boundary": "impl.boundary",
    "boolean": "impl.control-flow",
    "return": "impl.control-flow",
}
CLASSES = ("impl.comparison", "impl.boundary", "impl.control-flow")
CLASS_NOUNS = {
    "impl.comparison": "comparison",
    "impl.boundary": "boundary",
    "impl.control-flow": "branch/return",
}
KILLED = {"zapped", "timeout"}
# A mutant whose run ends in a collection/import/internal error is invalid (as in
# Stryker's RuntimeError/CompileError): neither caught nor missed, and reported apart.
INVALID = {"error"}
PRODUCERS = ("PRODUCER_PYTEST_GREMLINS", "PRODUCER_IMPLEMENTATION_FAULT_ADAPTER")


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


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
            foreign = owners_by_line[(scope["source"], line)] - family
            if foreign:
                shared_with.update(foreign)
            else:
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


def project_classes(plan: dict, report: dict, root: Path) -> dict[str, dict]:
    """Project one retained engine report onto the contract's Implementation classes.

    A class is exercised when at least one of its attributable faults is reached by a
    selected test, and detected only when every judged fault of that class is caught:
    an unreached fault is an undetected fault. Pardoned faults and faults that broke
    test collection are not judged, and are counted apart.
    """
    allowed = {
        (path, line)
        for path, lines in (plan.get("attributable_lines") or {}).items()
        for line in lines
    }
    rows = []
    for result in report.get("results") or []:
        raw_path = Path(str(result.get("file_path") or ""))
        try:
            relative = str(raw_path.resolve().relative_to(root.resolve()))
        except ValueError:
            relative = str(raw_path)
        line = int(result.get("line_number") or -1)
        fault_class = CLASS_BY_OPERATOR.get(str(result.get("operator") or ""))
        if fault_class is None or (relative, line) not in allowed:
            continue
        status = str(result.get("status") or "error")
        rows.append(
            {
                "id": str(result.get("gremlin_id") or ""),
                "class": fault_class,
                "operator": str(result.get("operator")),
                "description": str(result.get("description") or ""),
                "source": relative,
                "line": line,
                "status": status,
                "reached": bool(result.get("selected_tests")) or status in KILLED,
                "selected_tests": len(result.get("selected_tests") or []),
            }
        )
    classes = {}
    for fault_class in CLASSES:
        class_rows = [row for row in rows if row["class"] == fault_class]
        invalid = [row for row in class_rows if row["status"] in INVALID]
        judged = [row for row in class_rows if row["status"] != "pardoned" and row["status"] not in INVALID]
        killed = [row for row in judged if row["status"] in KILLED]
        reached = [row for row in judged if row["reached"]]
        survivors = [row for row in judged if row["status"] not in KILLED]
        unreached = [row for row in survivors if not row["reached"]]
        noun = CLASS_NOUNS[fault_class]

        def faults(count: int) -> str:
            return f"{count} {noun} fault" + ("" if count == 1 else "s")

        if not judged and invalid:
            basis = f"Every {noun} fault ({len(invalid)}) broke test collection, so none could be judged."
        elif not judged:
            basis = f"No {noun} fault site in the attributable code, so this class cannot be challenged here."
        elif not reached:
            basis = f"The contract's tests never reach its {faults(len(judged))}."
        elif len(killed) == len(judged):
            basis = (
                f"The contract's tests catch its only {noun} fault."
                if len(judged) == 1
                else f"The contract's tests catch all {faults(len(judged))}."
            )
        else:
            basis = (
                f"The contract's tests catch {len(killed)} of {faults(len(judged))}; "
                f"{len(survivors)} survive"
                + (f" ({len(unreached)} never reached)" if unreached else "")
                + "."
            )
        if judged and invalid:
            basis += f" {len(invalid)} more broke test collection and are not judged."
        classes[fault_class] = {
            "exercised": bool(reached),
            "detected": bool(judged) and len(killed) == len(judged),
            "generated": len(class_rows),
            "judged": len(judged),
            "reached": len(reached),
            "killed": len(killed),
            "survived": len(survivors),
            "unreached": len(unreached),
            "pardoned": len(class_rows) - len(judged) - len(invalid),
            "invalid": len(invalid),
            "survivors": [
                {k: row[k] for k in ("source", "line", "operator", "description", "reached")}
                for row in sorted(survivors, key=lambda row: (row["source"], row["line"], row["id"]))
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

# Anything that can change any contract's result is a shared input. Product code is
# deliberately shared: a mutant can push execution into code the unmutated run never
# touched, so no per-contract subset of the source can prove a result still holds.
SHARED_INPUT_SCOPE = (
    "src/llm_router/**/*.py",
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


def digest_map(root: Path, paths: set[str]) -> dict[str, str | None]:
    return {
        relative: (sha256_bytes((root / relative).read_bytes()) if (root / relative).is_file() else None)
        for relative in sorted(paths)
    }


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
    """The contract's own test inputs: test modules, their Gherkin and their cassettes."""
    rows = {row["nodeid"]: row for row in test_rows}
    paths: set[str] = set()
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


def engine_configuration() -> dict:
    plugin = Path(__file__).resolve().parent / "pytest_plugins/gremlins_full_pytest.py"
    return {
        "engine": GREMLINS_VERSION,
        "mode": "full pytest per mutant",
        "scope": "attributable @impl lines only",
        "operators": list(OPERATORS),
        "plugin_sha256": sha256_bytes(plugin.read_bytes()) if plugin.exists() else None,
        "hermetic_options": list(HERMETIC_OPTIONS),
    }


def plan_key(plan: dict) -> dict:
    return {"attributable_lines": plan.get("attributable_lines"), "tests": plan.get("tests")}


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
) -> dict[str, str]:
    """Environment shared by the outer engine run and every per-mutant pytest run.

    PYTEST_ADDOPTS reaches the per-mutant subprocesses too, so each of them runs
    with full pytest (lightweight runner disabled), fixed order, and, for the
    project suite, the same hermetic network rules as the retained run. A scope
    keeps only the mutants on those source lines.
    """
    scratch.mkdir(parents=True, exist_ok=True)
    scope_env: dict[str, str] = {}
    if scope is not None:
        scope_file = scratch / f"gremlin-scope-{sha256_bytes(stable_json(scope).encode())[:16]}.json"
        scope_file.write_text(stable_json(scope))
        scope_env["TERNFORGE_GREMLIN_SCOPE"] = str(scope_file)
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


def run_engine(root: Path, plan: dict, raw_path: Path, timeout: int = 5400) -> dict:
    """Run pytest-gremlins for one contract in place and retain its JSON report."""
    report_dir = root / "coverage/gremlins"
    coverage_dir_existed = (root / "coverage").exists()
    env = engine_env(
        Path(os.environ.get("TMPDIR", "/tmp")) / "ternforge-probe-scratch",
        scope=plan["attributable_lines"],
    )
    command = [*engine_command(root, plan["tests"], plan["files"]), "--no-cov"]
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
                {"results": [], "summary": {"total": 0}, "note": "no mutation site in the targets"},
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


def utc_now() -> str:
    return datetime.now(UTC).isoformat().replace("+00:00", "Z")
