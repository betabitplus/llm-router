"""pytest plugin: pytest-gremlins as the project's qualified mutation engine.

pytest-gremlins 1.9 ships a "lightweight runner" that imports test modules and calls
test functions without pytest. It cannot provide fixtures, parametrization or
pytest-bdd scenarios, and it reports every test it cannot call as a caught mutant,
so on a real suite it fabricates kills. Disabling it makes the engine fall back to
its own bootstrap, which runs the selected tests with full pytest for each mutant.

When TERNFORGE_GREMLIN_SCOPE names a JSON file mapping source paths to line numbers,
only mutants on those lines are kept. The filter runs after the engine generated and
numbered every mutant of the target files, so a kept mutant has the same id, the same
instrumented source and the same selected tests as in an unfiltered run; the others
are simply never executed.

The plugin also adds what the engine lacks (see ``ternforge_mutation``):

* the ``statement`` and ``body`` operators, planted by the engine's own switching
  transformer, and the Python operators (``argument``, ``condition``, ``conditional``,
  ``negation``, ``container``, ``conversion``, ``method``, ``attribute``, ``identity``,
  ``slice``), planted the same way on the calls, attributes, literals, comparisons,
  subscripts and conditions the engine does not reach;
* the arid-code rules of TERNFORGE_MUTATION_POLICY: a mutant in arid code is not
  planted and the report lists it under its rule;
* no mutant inside a type annotation, as mutmut leaves annotations alone: an
  annotation changes no call;
* the ``# mutation:`` pragma: a covered mutant is pardoned, so it never runs, and the
  report carries its category and reason;
* reach: every report entry says whether the contract's tests cover the mutated line.
  Code outside every function body (a module or class body, a decorator, a default
  value) runs when its module is imported, before any test: coverage records it for
  no test, the engine then runs every selected test for the mutant, as Stryker runs
  its static mutants, and the mutant counts as reached (``static``) when the tests
  import its module at all. With TERNFORGE_GREMLIN_SKIP_UNCOVERED=1 (the pull-request
  diff) an uncovered mutant is not run and is reported as not covered;
* for each mutant a stable fingerprint, its enclosing function or class, its exact
  location, the original code and the replacement;
* a confirmed time limit: the engine waits TERNFORGE_GREMLIN_TIMEOUT seconds for a
  mutant's tests and counts a longer run as caught, so a mutant that ran out of time runs
  once more with TERNFORGE_GREMLIN_CONFIRM_TIMEOUT seconds before it counts: a slow suite is
  no hang. The campaign sets both from the contract's measured test time
  (implementation_faults.time_limits); without them the limits are 30 s and 300 s.
"""

from __future__ import annotations

import ast
import copy
import dataclasses
import json
import os
import subprocess
from collections import Counter
from pathlib import Path

import pytest
import pytest_gremlins.plugin as _gremlins_plugin  # ty: ignore[unresolved-import]
import ternforge_mutation as tm
from pytest_gremlins.instrumentation import transformer as _transformer  # ty: ignore[unresolved-import]
from pytest_gremlins.instrumentation.gremlin import Gremlin  # ty: ignore[unresolved-import]
from pytest_gremlins.reporting.json_reporter import JsonReporter  # ty: ignore[unresolved-import]
from pytest_gremlins.reporting.results import (  # ty: ignore[unresolved-import]
    GremlinResult,
    GremlinResultStatus,
)

SCOPE_ENV = "TERNFORGE_GREMLIN_SCOPE"
POLICY_ENV = "TERNFORGE_MUTATION_POLICY"
SKIP_UNCOVERED_ENV = "TERNFORGE_GREMLIN_SKIP_UNCOVERED"
TIMEOUT_ENV = "TERNFORGE_GREMLIN_TIMEOUT"
CONFIRM_TIMEOUT_ENV = "TERNFORGE_GREMLIN_CONFIRM_TIMEOUT"
EXTENSION_SCHEMA = "ternforge-mutation-extension-1"
SIDECAR = "coverage/gremlins/ternforge-extension.json"

STATE: dict = {
    "sources": {},
    "meta": {},
    "body_spans": {},
    "reach": {},
    "static": set(),
    "files_reached": {},
    "skipped": set(),
    "not_planted": [],
    "filtered": Counter(),
    "pragmas": {},
    "policy": {},
}


def _no_lightweight_runner(*_args: object, **_kwargs: object) -> None:
    return None


def _scope_lines() -> set[tuple[str, int]] | None:
    scope_file = os.environ.get(SCOPE_ENV)
    if not scope_file:
        return None
    mapping = json.loads(Path(scope_file).read_text())
    return {
        (str(Path(path).resolve()), int(line))
        for path, lines in mapping.items()
        for line in lines
    }


def _policy() -> dict:
    policy_file = os.environ.get(POLICY_ENV)
    if not policy_file:
        return {"arid_rules": list(tm.ARID_RULES)}
    payload = json.loads(Path(policy_file).read_text())
    rules = list(payload.get("arid_rules") or [])
    unknown = sorted(set(rules) - set(tm.ARID_RULES))
    if unknown:
        raise pytest.UsageError(f"unknown arid rule(s) in {policy_file}: {', '.join(unknown)}")
    return {"arid_rules": rules}


# --- the extension's operators, planted by the engine's own transformer --------------

_registry = _transformer.get_default_registry()
for _operator in (tm.StatementRemoval, tm.BodyRemoval, *tm.PYTHON_OPERATORS):
    if _operator().name not in _registry.available():
        _registry.register(_operator)

# Where the project's modules live: the Python operators read a callee's parameters there.
PROJECT = tm.Project([Path.cwd() / "src", Path.cwd()])

_engine_description = _transformer._get_mutation_description


def _mutation_description(original, mutated, operator):  # noqa: ANN001, ANN202
    """A Python operator describes its own mutants; the engine describes its own."""
    describe = getattr(operator, "describe", None)
    return describe(original, mutated) if callable(describe) else _engine_description(original, mutated, operator)


_transformer._get_mutation_description = _mutation_description


def _enabled(transformer, name: str):
    return next((operator for operator in transformer._operators if operator.name == name), None)


def _visit_statement(self, node):
    self.generic_visit(node)
    operator = _enabled(self, "statement")
    if operator is None or not operator.can_mutate(node):
        return node
    source = STATE["sources"].get(self.file_path)
    start, end = tm.node_span(node)
    text = tm.source_segment(source.splitlines(), start, end) if source else tm.clean_source(node)
    gremlin = Gremlin(
        gremlin_id=self._next_gremlin_id(),
        file_path=self.file_path,
        line_number=node.lineno,
        original_node=node,
        mutated_node=ast.Pass(),
        operator_name="statement",
        description="removed " + tm.compact(text, 70),
    )
    self.gremlins.append(gremlin)
    return _transformer.build_switching_statement(node, [gremlin])


def _visit_function(self, node):
    operator = _enabled(self, "body")
    plan = tm.body_mutation_plan(node)[0] if operator is not None else []
    first = tm.first_executable(node.body)
    body = node.body[tm._docstring_offset(node.body):]
    body_span = (tm.node_span(body[0])[0], tm.node_span(body[-1])[1]) if body else None
    self.generic_visit(node)
    if not plan or first is None or body_span is None:
        return node
    guards = []
    for label, value in plan:
        gremlin = Gremlin(
            gremlin_id=self._next_gremlin_id(),
            file_path=self.file_path,
            # The first line the body runs: coverage marks it only when the function is called.
            line_number=first.lineno,
            original_node=node,
            mutated_node=ast.Return(value=value),
            operator_name="body",
            description=f"body → return {label}",
        )
        self.gremlins.append(gremlin)
        STATE["body_spans"][gremlin.gremlin_id] = body_span
        guards.append(
            ast.If(
                test=ast.Compare(
                    left=ast.Name(id="__gremlin_active__", ctx=ast.Load()),
                    ops=[ast.Eq()],
                    comparators=[ast.Constant(value=gremlin.gremlin_id)],
                ),
                body=[ast.Return(value=copy.deepcopy(value))],
                orelse=[],
            )
        )
    offset = tm._docstring_offset(node.body)
    node.body[offset:offset] = guards
    return node


def _visit_module(self, node):
    """Annotate the module once for the Python operators, then transform it."""
    tm.annotate(node, self.file_path, PROJECT)
    return self.generic_visit(node)


def _visit_expression(self, node):
    """Plant the Python operators on a call, an attribute read or a literal, as the engine plants
    its own on the expressions it visits."""
    self.generic_visit(node)
    gremlins = self._create_gremlins_for_node(node)
    if not gremlins:
        return node
    self.gremlins.extend(gremlins)
    return _transformer.build_switching_expression(node, gremlins)


def _visit_condition_owner(self, node):
    """Plant the operators that change a condition as a whole on the test of an if, a while or a
    conditional expression; the switch wraps the test as the other mutants left it."""
    original = node.test
    self.generic_visit(node)
    gremlins = [
        gremlin
        for operator in self._operators if operator.name in tm.TEST_OPERATORS and operator.can_mutate(original)
        for gremlin in _transformer.create_gremlins_for_node(original, operator, self.file_path, self._next_gremlin_id)
    ]
    if gremlins:
        self.gremlins.extend(gremlins)
        node.test = _transformer.build_switching_expression(node.test, gremlins)
    return node


_Transformer = _transformer.MutationSwitchingTransformer
_engine_operators_for = _Transformer._get_operators_for_node


def _operators_for(self, node):
    """The operators the engine's own visit may plant on a node: never one that changes a
    condition as a whole, which only its owner's visit plants."""
    return [operator for operator in _engine_operators_for(self, node) if operator.name not in tm.TEST_OPERATORS]


_Transformer._get_operators_for_node = _operators_for
for _name in ("visit_Expr", "visit_Assign", "visit_AnnAssign", "visit_AugAssign", "visit_Raise", "visit_Delete"):
    setattr(_Transformer, _name, _visit_statement)
_Transformer.visit_FunctionDef = _visit_function
_Transformer.visit_AsyncFunctionDef = _visit_function
_Transformer.visit_Module = _visit_module
for _name in ("visit_Call", "visit_Attribute", "visit_List", "visit_Tuple", "visit_Set", "visit_Dict", "visit_Subscript"):
    setattr(_Transformer, _name, _visit_expression)
for _name in ("visit_If", "visit_While", "visit_IfExp"):
    setattr(_Transformer, _name, _visit_condition_owner)


# --- scope, arid code, suppression and identity -------------------------------------


def _relative(path: str) -> str:
    resolved = Path(path).resolve()
    try:
        return str(resolved.relative_to(Path.cwd().resolve()))
    except ValueError:
        return str(resolved)


def _span(gremlin) -> tuple[tuple[int, int], tuple[int, int], int]:
    """Where a mutant sits: the span rules and pragmas judge, and its anchor line."""
    node = gremlin.original_node
    start, end = tm.node_span(node)
    anchor = int(getattr(node, "lineno", gremlin.line_number)) if gremlin.operator_name == "body" else start[0]
    return start, end, anchor


def _replacement(gremlin) -> str:
    if gremlin.operator_name == "statement":
        return "pass"
    if gremlin.operator_name == "body":
        return "return " + gremlin.description.split("return ", 1)[-1]
    if isinstance(gremlin.mutated_node, ast.Return) and gremlin.mutated_node.value is None:
        return "return None"
    return tm.clean_source(gremlin.mutated_node)


_generate_all_gremlins = _gremlins_plugin._generate_gremlins


def _generate_gremlins_in_scope(gremlin_session, source_files, rootdir) -> None:  # noqa: ANN001
    STATE["sources"].update(source_files)
    _generate_all_gremlins(gremlin_session, source_files, rootdir)
    scope = _scope_lines()
    policy = _policy()
    STATE["policy"] = policy
    operators = {operator.name for operator in gremlin_session.operators}
    trees, lines, regions, pragmas, qualnames, annotations, bodies = {}, {}, {}, {}, {}, {}, {}
    for path, source in source_files.items():
        try:
            trees[path] = ast.parse(source)
        except SyntaxError:
            continue
        lines[path] = source.splitlines()
        regions[path] = tm.arid_regions(trees[path], set(policy["arid_rules"]))
        pragmas[path] = tm.parse_pragmas(source, trees[path])
        qualnames[path] = tm.qualname_index(trees[path])
        annotations[path] = tm.annotation_spans(trees[path])
        bodies[path] = tm.function_body_spans(trees[path])

    def in_scope(path: str, line: int) -> bool:
        return scope is None or (str(Path(path).resolve()), int(line)) in scope

    kept = []
    occurrences: Counter = Counter()
    for gremlin in gremlin_session.gremlins:
        path = gremlin.file_path
        if not in_scope(path, gremlin.line_number) or path not in trees:
            continue
        start, end, anchor = _span(gremlin)
        location = STATE["body_spans"].get(gremlin.gremlin_id) or (start, end)
        qualname = tm.enclosing_qualname(qualnames[path], location[0], location[1])
        original = tm.compact(tm.source_segment(lines[path], start, end), 200)
        identity = (qualname, gremlin.operator_name, original if gremlin.operator_name != "body" else "", gremlin.description)
        occurrences[identity] += 1
        meta = {
            "fingerprint": tm.fingerprint(_relative(path), *identity, occurrences[identity]),
            "qualname": qualname,
            "location": location,
            "anchor_line": anchor,
            "original": original,
            "replacement": _replacement(gremlin),
        }
        # An annotation changes no call: its mutants are dropped, after they were counted, so every
        # other mutant keeps the fingerprint it had.
        if gremlin.operator_name != "body" and tm.within(annotations[path], start, end):
            STATE["filtered"]["annotation: changes no call"] += 1
            continue
        if gremlin.operator_name != "body" and not tm.within(bodies[path], start, end):
            STATE["static"].add(gremlin.gremlin_id)
        rule = next((region.rule for region in regions[path] if region.contains(start, end)), None)
        if rule:
            STATE["not_planted"].append(
                {
                    "gremlin_id": gremlin.gremlin_id,
                    "file_path": path,
                    "line_number": gremlin.line_number,
                    "operator": gremlin.operator_name,
                    "description": gremlin.description,
                    "rule": rule,
                    **{key: meta[key] for key in ("fingerprint", "qualname", "original", "replacement")},
                    "location": _mte_location(location),
                }
            )
            continue
        pragma = next(
            (item for item in pragmas[path] if item.covers(gremlin.operator_name, anchor, start, end)),
            None,
        )
        if pragma is not None:
            pragma.matched += 1
            gremlin = dataclasses.replace(
                gremlin, pardoned=True, pardon_reason=f"{pragma.category}: {pragma.reason}"
            )
            meta["suppression"] = {"category": pragma.category, "reason": pragma.reason, "line": pragma.line}
        STATE["meta"][gremlin.gremlin_id] = meta
        kept.append(gremlin)
    gremlin_session.gremlins = kept

    # What the validity filter kept out of the argument operator in the scoped code: a keyword
    # the project's callee requires.
    if "argument" in operators:
        for path, tree in trees.items():
            tm.annotate(tree, path, PROJECT)
            for node in ast.walk(tree):
                if isinstance(node, ast.Call) and in_scope(path, node.lineno):
                    STATE["filtered"]["argument: required parameter"] += sum(
                        keyword.arg in (getattr(node, "_tf_required", set()) or set()) for keyword in node.keywords
                    )
    # What the validity filter kept out of the body operator in the scoped code.
    if "body" in operators:
        for path, tree in trees.items():
            for node in ast.walk(tree):
                if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    continue
                first = tm.first_executable(node.body)
                if first is None or not in_scope(path, first.lineno):
                    continue
                plan, reason = tm.body_mutation_plan(node)
                if not plan and reason:
                    STATE["filtered"][f"body: {reason}"] += 1
    STATE["pragmas"] = {
        _relative(path): [pragma.record() for pragma in items]
        for path, items in pragmas.items()
        if items
    }
    # The engine writes no report when nothing is left to run; what the rules, the filter and the
    # pragmas decided is kept beside it anyway, for the adapter to retain.
    sidecar = Path.cwd() / SIDECAR
    sidecar.parent.mkdir(parents=True, exist_ok=True)
    sidecar.write_text(json.dumps({"ternforge": _extension_section()}, indent=2, sort_keys=True))


# --- reach, the pull-request skip, and the enriched report ---------------------------

_select_tests = _gremlins_plugin._select_tests_for_gremlin_prioritized


def _file_reached(selector, file_path: str) -> bool:  # noqa: ANN001
    """Whether any selected test runs a line of the file, so the tests import its module."""
    reached = STATE["files_reached"].get(file_path)
    if reached is None:
        reached = any(path == file_path for path, _line in selector.coverage_map.locations())
        STATE["files_reached"][file_path] = reached
    return reached


def _select_tests_recording_reach(gremlin, gremlin_session):  # noqa: ANN001
    selector = gremlin_session.prioritized_selector
    if selector is not None and not gremlin_session.no_coverage_filter:
        reached = bool(selector.select_tests_prioritized(gremlin))
        # Import-time code: coverage names no test for it, the engine runs every selected test.
        if not reached and gremlin.gremlin_id in STATE["static"]:
            reached = _file_reached(selector, gremlin.file_path)
        STATE["reach"][gremlin.gremlin_id] = reached
    return _select_tests(gremlin, gremlin_session)


_test_gremlin = _gremlins_plugin._test_gremlin


class _TimeLimited:
    """The engine's ``subprocess`` with another time limit for a mutant's tests."""

    def __init__(self, seconds: float) -> None:
        self.seconds = seconds

    def run(self, *args, **kwargs):  # noqa: ANN002, ANN003, ANN201
        if "timeout" in kwargs:
            kwargs["timeout"] = self.seconds
        return subprocess.run(*args, **kwargs)  # noqa: PLW1510 - the engine passes check itself

    def __getattr__(self, name: str):  # noqa: ANN204
        return getattr(subprocess, name)


def _test_within(gremlin, test_command, rootdir, instrumented_dir, seconds: float):  # noqa: ANN001, ANN201
    engine_subprocess = _gremlins_plugin.subprocess
    _gremlins_plugin.subprocess = _TimeLimited(seconds)
    try:
        return _test_gremlin(gremlin, test_command, rootdir, instrumented_dir)
    finally:
        _gremlins_plugin.subprocess = engine_subprocess


def _test_gremlin_unless_uncovered(gremlin, test_command, rootdir, instrumented_dir):  # noqa: ANN001
    if os.environ.get(SKIP_UNCOVERED_ENV) == "1" and STATE["reach"].get(gremlin.gremlin_id) is False:
        STATE["skipped"].add(gremlin.gremlin_id)
        return GremlinResult(gremlin=gremlin, status=GremlinResultStatus.SURVIVED)
    result = _test_within(gremlin, test_command, rootdir, instrumented_dir, float(os.environ.get(TIMEOUT_ENV) or 30))
    if result.status == GremlinResultStatus.TIMEOUT:
        # A slow suite is no hang: the time limit catches a mutant only when a run with room to spare times out too.
        result = _test_within(gremlin, test_command, rootdir, instrumented_dir, float(os.environ.get(CONFIRM_TIMEOUT_ENV) or 300))
    return result


def _mte_location(location) -> dict:
    (start_line, start_col), (end_line, end_col) = location
    return {
        "start": {"line": start_line, "column": start_col + 1},
        "end": {"line": end_line, "column": end_col + 1},
    }


_build_result = JsonReporter._build_result


def _build_result_enriched(self, result):  # noqa: ANN001
    entry = _build_result(self, result)
    gremlin_id = result.gremlin.gremlin_id
    meta = STATE["meta"].get(gremlin_id) or {}
    if meta:
        entry.update(
            {
                "fingerprint": meta["fingerprint"],
                "qualname": meta["qualname"],
                "location": _mte_location(meta["location"]),
                "anchor_line": meta["anchor_line"],
                "original": meta["original"],
                "replacement": meta["replacement"],
            }
        )
        if meta.get("suppression"):
            entry["suppression"] = meta["suppression"]
    entry["origin"] = "rule"
    entry["covered"] = STATE["reach"].get(gremlin_id)
    if gremlin_id in STATE["static"]:
        entry["static"] = True
    if gremlin_id in STATE["skipped"]:
        entry["run_skipped"] = "not covered"
    return entry


_build_report_data = JsonReporter._build_report_data


def _extension_section() -> dict:
    return {
        "schema": EXTENSION_SCHEMA,
        "arid_rules": list((STATE["policy"] or {}).get("arid_rules") or []),
        "skip_uncovered": os.environ.get(SKIP_UNCOVERED_ENV) == "1",
        "not_planted": list(STATE["not_planted"]),
        "filtered": dict(sorted(STATE["filtered"].items())),
        "pragmas": STATE["pragmas"],
    }


def _build_report_data_enriched(self, score):  # noqa: ANN001
    data = _build_report_data(self, score)
    data["ternforge"] = _extension_section()
    return data


_gremlins_plugin.build_lightweight_command = _no_lightweight_runner
_gremlins_plugin._generate_gremlins = _generate_gremlins_in_scope
_gremlins_plugin._select_tests_for_gremlin_prioritized = _select_tests_recording_reach
_gremlins_plugin._test_gremlin = _test_gremlin_unless_uncovered
JsonReporter._build_result = _build_result_enriched
JsonReporter._build_report_data = _build_report_data_enriched
