"""Scenario oracle mutants (050): does a Gherkin scenario check the outcome it names?

A Then step's definition compares what happened with what the scenario expects. Each mutant changes
that expectation in one step definition, in a copy of the project, and nothing else: a constant the
step compares with becomes another value of its type (``== "big"`` becomes ``== "big·"``), or the
expected type or error an assertion helper is given becomes another one the same module names
(``_assert_error(case, ConfigurationError.__name__)`` becomes ``... ProviderError.__name__``). The
scenarios that use the step run as the retained run runs them, and one of them must fail. When they
all still pass, the step does not check the outcome it names, and would pass as well when the product
gave another outcome: the Test Plan's ``spec.wrong-outcome``, challenged at the level of the
specification. Only the step's own comparison changes, so a failure is that comparison's; a run that
cannot collect or build the scenario is invalid and tells nothing.

No model is asked: Python's own parser reads the step definitions, the official Gherkin parser the
features, and pytest-bdd runs them. The pilot's first probe of this kind, for one requirement, is
``probe_invalid_config_specification_fault``; this generalizes it to every Then step.
"""

from __future__ import annotations

import ast
import copy
import hashlib
import json
import re
import shutil
import subprocess
import tempfile
import xml.etree.ElementTree as ET
from pathlib import Path

from gherkin.parser import Parser

SCHEMA = "ternforge-scenario-mutants-1"
MUTANTS_PER_STEP = 2
CONTRACT_TAG = re.compile(r"@((?:REQ|TREQ)_[A-Z0-9_]+)\[revision==(\d+)\]")
# A run that cannot collect or build the scenario says nothing about the check.
INVALID_FAILURES = re.compile(r"StepDefinitionNotFoundError|FixtureLookupError|fixture '.+' not found|ImportError|SyntaxError|collection")
HERMETIC_OPTIONS = ("--record-mode=none", "--block-network", "--allowed-hosts=localhost,127\\.0\\.0\\.1", "--no-cov", "-p", "no:cacheprovider", "-q")


def python_name(name: str) -> str:
    """The test name pytest-bdd gives a scenario that ``scenarios()`` binds."""
    return "test_" + re.sub(r"\W+", "_", name.lower()).strip("_")


# --- the scenarios and the modules that bind them ------------------------------------------------


def _scenarios(children: list[dict], tags: tuple[str, ...] = ()):
    """Every scenario with the tags of the rule it sits in."""
    for child in children:
        if "rule" in child:
            rule = child["rule"]
            yield from _scenarios(rule.get("children") or [], (*tags, *(tag["name"] for tag in rule.get("tags") or [])))
        elif "scenario" in child:
            yield child["scenario"], tags


def feature_bindings(root: Path) -> dict[str, str]:
    """Which test module binds each feature, relative to the features folder."""
    found = {}
    for path in sorted((root / "tests").rglob("test_*.py")):
        for match in re.finditer(r"""\bscenarios?\(\s*["']([^"']+\.feature)["']""", path.read_text()):
            found.setdefault(match.group(1), str(path.relative_to(root)))
    return found


# A plugin that lists, at collection, the test pytest-bdd made for each scenario.
COLLECTOR = """
import json, os

def pytest_collection_modifyitems(session, config, items):
    found = []
    for item in items:
        scenario = getattr(getattr(item, "obj", None), "__scenario__", None)
        if scenario is not None:
            found.append({"nodeid": item.nodeid.split("[", 1)[0], "feature": str(scenario.feature.filename), "scenario": scenario.name})
    with open(os.environ["TERNFORGE_SCENARIO_MAP"], "w") as handle:
        json.dump(found, handle)
"""


def collected_tests(root: Path, pytest: Path) -> dict[tuple[str, str], str]:
    """The test of each scenario, as pytest collects it: (feature, scenario) → node id. A module may
    name its scenario tests itself, so the name pytest-bdd would give is only the fallback."""
    with tempfile.TemporaryDirectory(prefix="ternforge-scenario-map-") as scratch:
        (Path(scratch) / "ternforge_scenario_map.py").write_text(COLLECTOR)
        out = Path(scratch) / "map.json"
        env = {"PYTHONPATH": f"{scratch}:{root / 'src'}:{root}", "PATH": "/usr/bin:/bin", "PYTHONDONTWRITEBYTECODE": "1", "TERNFORGE_SCENARIO_MAP": str(out)}
        subprocess.run(
            [str(pytest), "--collect-only", "-q", "-p", "ternforge_scenario_map", "--no-cov", "-p", "no:cacheprovider", "tests"],
            cwd=root, env=env, text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=600, check=False,
        )
        rows = json.loads(out.read_text()) if out.is_file() else []
    features = (root / "features").resolve()
    found = {}
    for row in rows:
        try:
            relative = str(Path(row["feature"]).resolve().relative_to(features))
        except ValueError:
            continue
        found.setdefault((relative, row["scenario"]), row["nodeid"])
    return found


def scenarios(root: Path, pytest: Path | None = None) -> list[dict]:
    """Every scenario a module binds: its feature, its steps as written, its contracts and its test."""
    bindings = feature_bindings(root)
    tests = collected_tests(root, pytest) if pytest is not None else {}
    found = []
    for path in sorted((root / "features").rglob("*.feature")):
        relative = str(path.relative_to(root / "features"))
        feature = Parser().parse(path.read_text()).get("feature") or {}
        feature_tags = [tag["name"] for tag in feature.get("tags") or []]
        for scenario, rule_tags in _scenarios(feature.get("children") or []):
            tags = [*feature_tags, *rule_tags, *(tag["name"] for tag in scenario.get("tags") or [])]
            module = bindings.get(relative)
            steps = [step["text"] for step in scenario.get("steps") or []]
            # An outline's steps name its columns; each row of its examples fills them in.
            rows = [
                {cell_head["value"]: cell["value"] for cell_head, cell in zip(table["tableHeader"]["cells"], row["cells"], strict=False)}
                for table in scenario.get("examples") or [] if table.get("tableHeader") for row in table.get("tableBody") or []
            ]
            texts = sorted({re.sub(r"<([^>]+)>", lambda match, values=values: values.get(match.group(1), match.group(0)), text) for values in rows for text in steps}) if rows else steps
            found.append({
                "feature": relative, "scenario": scenario["name"], "module": module, "steps": texts,
                "contracts": sorted({f"{name}[revision=={revision}]" for tag in tags for name, revision in CONTRACT_TAG.findall(tag)}),
                "nodeid": tests.get((relative, scenario["name"])) or (f"{module}::{python_name(scenario['name'])}" if module else None),
            })
    return found


# --- the Then step definitions and their expectations --------------------------------------------


def _decorator_pattern(decorator: ast.expr) -> tuple[str, str] | None:
    """The kind and text of a ``@then`` decorator's step pattern: plain, parse or re."""
    if not isinstance(decorator, ast.Call) or not decorator.args:
        return None
    name = ast.unparse(decorator.func).split(".")[-1]
    if name != "then":
        return None
    first = decorator.args[0]
    if isinstance(first, ast.Constant) and isinstance(first.value, str):
        return "plain", first.value
    if isinstance(first, ast.Call) and first.args and isinstance(first.args[0], ast.Constant) and isinstance(first.args[0].value, str):
        kind = ast.unparse(first.func).split(".")[-1]
        return ("re" if kind == "re" else "parse"), first.args[0].value
    return None


def step_matches(kind: str, pattern: str, text: str) -> bool:
    if kind == "plain":
        return text == pattern
    if kind == "re":
        return re.fullmatch(pattern, text) is not None
    import parse  # the library pytest-bdd's parsers.parse is built on

    return parse.compile(pattern).parse(text) is not None


ASSERTING = re.compile(r"^_*(assert|check|expect|verify|require)")


def _called(node: ast.AST) -> str:
    """The last part of the name a call calls: ``x.assert_error(...)`` → ``assert_error``."""
    return ast.unparse(node.func).split(".")[-1] if isinstance(node, ast.Call) else ""


def _expectation_nodes(function: ast.AST) -> list[ast.AST]:
    """What a function compares with: the constant side of an asserted comparison, the constant or
    ``Name.__name__`` arguments of an assertion helper it calls, and, for an assertion with neither,
    the assertion's test itself (then negated)."""
    found = []
    for node in ast.walk(function):
        if isinstance(node, ast.Assert):
            constants = [
                side for side in ((node.test.left, *node.test.comparators) if isinstance(node.test, ast.Compare) else ())
                if isinstance(side, ast.Constant) and not isinstance(side.value, bool) and side.value is not None
            ]
            if not constants:
                node.test._tf_assert_test = True  # ty: ignore[unresolved-attribute]
            found.extend(constants or [node.test])
        elif isinstance(node, ast.Call) and ASSERTING.match(_called(node)):
            for argument in node.args[1:]:
                if isinstance(argument, ast.Constant) or (isinstance(argument, ast.Attribute) and argument.attr == "__name__"):
                    found.append(argument)
    return found


def _checks_here(function: ast.AST) -> bool:
    return any(
        isinstance(node, ast.Assert) or (isinstance(node, ast.Call) and ASSERTING.match(_called(node)))
        or (isinstance(node, ast.With) and "raises" in ast.unparse(node))
        for node in ast.walk(function)
    )


def _other_value(node: ast.AST, names: list[str]) -> ast.AST | None:
    """Another expectation of the same type: a changed constant, another name the module expects,
    or, for an assertion's own test, its negation."""
    if getattr(node, "_tf_assert_test", False):
        return ast.UnaryOp(op=ast.Not(), operand=copy.deepcopy(node))
    if isinstance(node, ast.Constant):
        value = node.value
        if isinstance(value, str):
            return ast.Constant(value=value + "·")
        if isinstance(value, int | float):
            return ast.Constant(value=value + 1)
        return None
    if isinstance(node, ast.Attribute) and isinstance(node.value, ast.Name):
        others = [name for name in names if name != node.value.id]
        if others:
            return ast.Attribute(value=ast.Name(id=others[0], ctx=ast.Load()), attr=node.attr, ctx=ast.Load())
    return None


class _Modules:
    """The test modules and the support helpers they import, each parsed once."""

    def __init__(self, root: Path) -> None:
        self.root = root
        self.trees: dict[str, ast.Module] = {}

    def tree(self, relative: str) -> ast.Module:
        if relative not in self.trees:
            self.trees[relative] = ast.parse((self.root / relative).read_text())
        return self.trees[relative]

    def functions(self, relative: str) -> dict[str, ast.AST]:
        return {node.name: node for node in self.tree(relative).body if isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef)}

    def imported(self, relative: str) -> dict[str, tuple[str, str]]:
        """The helpers a module imports from the project's test code: name → (file, function)."""
        found = {}
        for node in self.tree(relative).body:
            if isinstance(node, ast.ImportFrom) and node.module and node.module.startswith("tests."):
                path = Path(*node.module.split(".")).with_suffix(".py")
                if (self.root / path).is_file():
                    for alias in node.names:
                        found[alias.asname or alias.name] = (str(path), alias.name)
        return found

    def reach(self, relative: str, function: ast.AST) -> list[tuple[str, ast.AST]]:
        """The function and every function of the test code it calls, transitively."""
        seen, queue, found = set(), [(relative, function)], []
        while queue:
            where, node = queue.pop(0)
            if (where, node.name) in seen:
                continue
            seen.add((where, node.name))
            found.append((where, node))
            local, imported = self.functions(where), self.imported(where)
            for call in (item for item in ast.walk(node) if isinstance(item, ast.Call) and isinstance(item.func, ast.Name)):
                name = call.func.id
                if name in local:
                    queue.append((where, local[name]))
                elif name in imported:
                    target, item = imported[name]
                    if item in self.functions(target):
                        queue.append((target, self.functions(target)[item]))
        return found


def generate(root: Path, pytest: Path | None = None) -> list[dict]:
    """Every expectation mutant of every function a Then step checks with, run by every bound scenario
    that uses such a step, and every Then step that checks nothing; in a stable order."""
    bound = scenarios(root, pytest)
    modules = _Modules(root)
    users: dict[tuple[str, str], list[dict]] = {}
    unchecked: list[dict] = []
    for path in sorted((root / "tests").rglob("*.py")):
        relative = str(path.relative_to(root))
        if "then(" not in path.read_text():
            continue
        for node in modules.tree(relative).body:
            if not isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef):
                continue
            patterns = [found for decorator in node.decorator_list if (found := _decorator_pattern(decorator))]
            if not patterns:
                continue
            kind, pattern = patterns[0]
            using = [
                scenario for scenario in bound
                if scenario["nodeid"] and (relative.endswith("conftest.py") or scenario["module"] == relative)
                and any(step_matches(kind, pattern, text) for text in scenario["steps"])
            ]
            if not using:
                continue
            reached = modules.reach(relative, node)
            if not any(_checks_here(function) for _where, function in reached):
                unchecked.append({"module": relative, "step": pattern, "function": node.name, "line": int(node.lineno), "scenarios": using})
                continue
            for where, function in reached:
                bucket = users.setdefault((where, function.name), [])
                bucket.extend(scenario for scenario in using if scenario not in bucket)
    mutants = []
    for (where, name), using in sorted(users.items()):
        tree = modules.tree(where)
        function = modules.functions(where)[name]
        # The expected names the module's own assertions use: an exception, a type.
        names = sorted({
            node.value.id for candidate in modules.functions(where).values() for node in _expectation_nodes(candidate)
            if isinstance(node, ast.Attribute) and isinstance(node.value, ast.Name)
        })
        made = 0
        for index, expected in enumerate(_expectation_nodes(function)):
            replacement = _other_value(expected, names)
            if replacement is None or made >= MUTANTS_PER_STEP:
                continue
            made += 1
            mutated = copy.deepcopy(tree)
            target = next(node for node in mutated.body if isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef) and node.name == name)
            spot = _expectation_nodes(target)[index]
            for parent in ast.walk(target):
                for field, value in ast.iter_fields(parent):
                    if value is spot:
                        setattr(parent, field, replacement)
                    elif isinstance(value, list) and spot in value:
                        value[value.index(spot)] = replacement
            identity = f"{where}|{name}|{index}|{ast.unparse(expected)}|{ast.unparse(replacement)}"
            mutants.append({
                "id": hashlib.sha256(identity.encode()).hexdigest()[:16],
                "module": where, "function": name, "line": int(expected.lineno),
                "original": ast.unparse(expected), "replacement": ast.unparse(replacement),
                "source": ast.unparse(ast.fix_missing_locations(mutated)),
                "scenarios": [{key: scenario[key] for key in ("feature", "scenario", "nodeid", "contracts")} for scenario in using],
            })
    for row in unchecked:
        identity = f"{row['module']}|{row['function']}|unchecked"
        mutants.append({
            "id": hashlib.sha256(identity.encode()).hexdigest()[:16], "module": row["module"], "function": row["function"],
            "line": row["line"], "original": "", "replacement": "", "unchecked": True,
            "scenarios": [{key: scenario[key] for key in ("feature", "scenario", "nodeid", "contracts")} for scenario in row["scenarios"]],
        })
    return mutants


# --- running them ----------------------------------------------------------------------------------


def classify(returncode: int, junit: Path, output: str) -> tuple[str, str]:
    """What the runs of one mutant came to: caught, survived or invalid, with why."""
    failures = []
    if junit.is_file():
        for case in ET.parse(junit).getroot().iter("testcase"):
            for kind in ("failure", "error"):
                for element in case.findall(kind):
                    failures.append((kind, " ".join(f"{element.get('message') or ''} {element.text or ''}".split())))
    if returncode == 0 and not failures:
        return "survived", "every scenario that uses the step passes with the other expectation"
    if returncode in {2, 3, 4, 5}:
        return "invalid", f"pytest could not run the scenarios (exit {returncode})"
    text = " ".join(detail for _kind, detail in failures) or output
    if INVALID_FAILURES.search(text) and not any(kind == "failure" and "AssertionError" in detail for kind, detail in failures):
        return "invalid", INVALID_FAILURES.search(text).group(0)
    if any(kind == "failure" for kind, _detail in failures):
        return "caught", next(detail for kind, detail in failures if kind == "failure")[:200]
    return "invalid", text[:200] or f"pytest exited {returncode}"


def run(root: Path, mutants: list[dict], pytest: Path, timeout: int = 300) -> list[dict]:
    """Run every mutant in one copy of the project, restoring each module after its mutant."""
    results = []
    with tempfile.TemporaryDirectory(prefix="ternforge-scenario-mutants-") as scratch:
        work = Path(scratch) / "copy"
        work.mkdir()
        for name in ("src", "tests", "features", "examples"):
            if (root / name).exists():
                shutil.copytree(root / name, work / name, ignore=shutil.ignore_patterns("__pycache__", ".pytest_cache"))
        shutil.copy2(root / "pyproject.toml", work / "pyproject.toml")
        env = {"PYTHONPATH": f"{work / 'src'}:{work}", "PYTHONDONTWRITEBYTECODE": "1", "PATH": "/usr/bin:/bin"}
        for mutant in mutants:
            if mutant.get("unchecked"):
                results.append({**mutant, "outcome": "unchecked", "reason": "the step names an outcome and checks none"})
                continue
            module = work / mutant["module"]
            original = module.read_text()
            junit = Path(scratch) / f"{mutant['id']}.xml"
            try:
                module.write_text(mutant["source"] + "\n")
                done = subprocess.run(
                    [str(pytest), *[scenario["nodeid"] for scenario in mutant["scenarios"]], *HERMETIC_OPTIONS, f"--junitxml={junit}"],
                    cwd=work, env=env, text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=timeout, check=False,
                )
                outcome, reason = classify(done.returncode, junit, done.stdout[-2000:])
            except subprocess.TimeoutExpired:
                outcome, reason = "invalid", f"the scenarios ran out of their {timeout} s"
            finally:
                module.write_text(original)
            results.append({**{key: value for key, value in mutant.items() if key != "source"}, "outcome": outcome, "reason": reason})
    return results


def main(argv: list[str]) -> int:
    """``scenario_mutants.py generate|run ROOT [OUT]``: list the mutants, or run them and write the results."""
    if len(argv) < 2 or argv[0] not in {"generate", "run"}:
        print(main.__doc__)
        return 2
    root = Path(argv[1]).resolve()
    mutants = generate(root, root / ".venv/bin/pytest")
    if argv[0] == "generate":
        print(json.dumps([{key: value for key, value in mutant.items() if key != "source"} for mutant in mutants], indent=1))
        return 0
    results = run(root, mutants, root / ".venv/bin/pytest")
    if len(argv) > 2:
        Path(argv[2]).write_text(json.dumps({"schema": SCHEMA, "results": results}, indent=1, sort_keys=True) + "\n")
    counts: dict[str, int] = {}
    for row in results:
        counts[row["outcome"]] = counts.get(row["outcome"], 0) + 1
    print(json.dumps(counts))
    return 0


if __name__ == "__main__":
    import sys

    raise SystemExit(main(sys.argv[1:]))
