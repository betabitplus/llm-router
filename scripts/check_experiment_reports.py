"""Validate self-contained Engineering Experiment capsules and captured reports."""

from __future__ import annotations

import ast
import hashlib
import re
import sys
import tomllib
from pathlib import Path

import nbformat

ROOT = Path(__file__).resolve().parents[1]
EXPERIMENTS_ROOT = ROOT / "experiments" / "llm_router"
CAPSULE_PATTERN = re.compile(r"^exp_(?P<number>[0-9]{4})_[a-z0-9_]+$")
ID_PATTERN = re.compile(r"^EXP_[0-9]{4}$")
STEP_PATTERN = re.compile(r"^## (?P<number>[1-9][0-9]*)\. (?P<title>\S.+)$")
ROLE_TAGS = {
    "exp-meta",
    "exp-question",
    "exp-setup",
    "exp-step",
    "exp-evidence",
    "exp-conclusion",
}
REQUIRED_FILES = (
    "src/experiment.py",
    "report/report.ipynb",
    "pyproject.toml",
    "uv.lock",
    ".python-version",
)
FORBIDDEN_IMPORT_ROOTS = {"experiments", "llm_router", "src", "tests"}


def _tags(cell: nbformat.NotebookNode) -> set[str]:
    return {str(tag) for tag in cell.metadata.get("tags", [])}


def _role(cell: nbformat.NotebookNode) -> str:
    roles = _tags(cell) & ROLE_TAGS
    if len(roles) != 1:
        message = f"expected exactly one experiment role tag, got {sorted(roles)}"
        raise ValueError(message)
    return next(iter(roles))


def _digest_file(hasher: hashlib._Hash, root: Path, path: Path) -> None:
    relative = path.relative_to(root).as_posix().encode()
    hasher.update(len(relative).to_bytes(8, "big"))
    hasher.update(relative)
    if path.suffix == ".py":
        tree = ast.parse(path.read_text(), filename=str(path), type_comments=True)
        data = ast.dump(tree, include_attributes=False).encode()
    else:
        data = path.read_bytes()
    hasher.update(len(data).to_bytes(8, "big"))
    hasher.update(data)


def capsule_digest(capsule: Path, notebook: nbformat.NotebookNode | None = None) -> str:
    hasher = hashlib.sha256()
    paths: list[Path] = []
    for directory in (capsule / "src", capsule / "inputs"):
        if not directory.is_dir():
            continue
        for path in directory.rglob("*"):
            relative_parts = path.relative_to(capsule).parts
            if (
                not path.is_file()
                or "__pycache__" in relative_parts
                or path.suffix == ".pyc"
            ):
                continue
            paths.append(path)
    paths.extend(
        capsule / name for name in ("pyproject.toml", "uv.lock", ".python-version")
    )
    for path in sorted(paths, key=lambda item: item.relative_to(capsule).as_posix()):
        _digest_file(hasher, capsule, path)

    if notebook is None:
        notebook = nbformat.read(capsule / "report" / "report.ipynb", as_version=4)
    for index, cell in enumerate(notebook.cells):
        if cell.cell_type != "code":
            continue
        marker = f"report-code:{index}".encode()
        tree = ast.parse(str(cell.source), filename=f"report-code:{index}")
        source = ast.dump(tree, include_attributes=False).encode()
        hasher.update(len(marker).to_bytes(8, "big"))
        hasher.update(marker)
        hasher.update(len(source).to_bytes(8, "big"))
        hasher.update(source)
    return hasher.hexdigest()


def _validate_layout(capsule: Path) -> list[str]:
    errors: list[str] = []
    match = CAPSULE_PATTERN.fullmatch(capsule.name)
    if match is None:
        return ["capsule directory must match exp_####_<slug>"]
    for relative in REQUIRED_FILES:
        if not (capsule / relative).is_file():
            errors.append(f"missing required file: {relative}")
    for forbidden in ("shared", "_support"):
        if (capsule / forbidden).exists():
            errors.append(f"forbidden shared experiment directory: {forbidden}")
    for directory in (capsule / "inputs", capsule / "artifacts"):
        if not directory.exists():
            continue
        for path in directory.rglob("*.py"):
            errors.append(
                f"Python source belongs under src/, not {path.relative_to(capsule)}"
            )
    for path in capsule.rglob("*"):
        if ".venv" in path.relative_to(capsule).parts:
            continue
        if not path.is_symlink():
            continue
        try:
            path.resolve().relative_to(capsule.resolve())
        except ValueError:
            errors.append(f"symlink escapes capsule: {path.relative_to(capsule)}")
    return errors


def _validate_pyproject(capsule: Path) -> list[str]:
    path = capsule / "pyproject.toml"
    if not path.is_file():
        return []
    data = tomllib.loads(path.read_text())
    errors: list[str] = []
    dependencies = list(data.get("project", {}).get("dependencies", []))
    groups = data.get("dependency-groups", {})
    for values in groups.values():
        dependencies.extend(values)
    for dependency in dependencies:
        lowered = str(dependency).lower()
        if " @ file:" in lowered or "../" in lowered or "./" in lowered:
            errors.append(f"local/path dependency is forbidden: {dependency}")
    sources = data.get("tool", {}).get("uv", {}).get("sources", {})
    for name, source in sources.items():
        if isinstance(source, dict) and any(
            key in source for key in ("path", "workspace")
        ):
            errors.append(f"uv source {name!r} must not use path/workspace coupling")
    return errors


def _validate_imports(capsule: Path) -> list[str]:
    errors: list[str] = []
    src = capsule / "src"
    if not src.is_dir():
        return errors
    for path in sorted(src.rglob("*.py")):
        try:
            tree = ast.parse(path.read_text(), filename=str(path))
        except SyntaxError as exc:
            errors.append(f"invalid Python in {path.relative_to(capsule)}: {exc}")
            continue
        for node in ast.walk(tree):
            names: list[str] = []
            if isinstance(node, ast.Import):
                names.extend(alias.name for alias in node.names)
            elif isinstance(node, ast.ImportFrom) and node.module:
                names.append(node.module)
            for name in names:
                root = name.split(".", 1)[0]
                if root in FORBIDDEN_IMPORT_ROOTS:
                    relative = path.relative_to(capsule)
                    errors.append(
                        f"forbidden external project import in {relative}: {name}"
                    )
    return errors


def _extract_need_id(source: str) -> str | None:
    match = re.search(r"(?m)^:id:\s*(EXP_[0-9]{4})\s*$", source)
    return None if match is None else match.group(1)


def _validate_report(capsule: Path) -> list[str]:
    report = capsule / "report" / "report.ipynb"
    if not report.is_file():
        return []
    try:
        notebook = nbformat.read(report, as_version=4)
        nbformat.validate(notebook)
    except Exception as exc:
        return [f"invalid notebook: {exc}"]

    errors: list[str] = []
    roles: list[str] = []
    for index, cell in enumerate(notebook.cells):
        try:
            roles.append(_role(cell))
        except ValueError as exc:
            errors.append(f"cell {index}: {exc}")
    if errors:
        return errors

    expected_prefix = ["exp-meta", "exp-question", "exp-setup"]
    if roles[:3] != expected_prefix or roles[-1] != "exp-conclusion":
        errors.append(
            "report must start Meta -> Question -> Setup and end with Conclusion"
        )
    middle = roles[3:-1]
    if len(middle) == 0 or len(middle) % 2:
        errors.append("report must contain one or more Step -> Evidence pairs")
    else:
        for index in range(0, len(middle), 2):
            if middle[index : index + 2] != ["exp-step", "exp-evidence"]:
                errors.append(
                    "report body must repeat Step -> Evidence in strict order"
                )
                break

    meta = notebook.cells[0]
    if meta.cell_type != "markdown":
        errors.append("metadata cell must be Markdown")
    else:
        source = str(meta.source)
        if source.count("```{exp}") != 1:
            errors.append("metadata cell must contain exactly one EXP need")
        need_id = _extract_need_id(source)
        if need_id is None or not ID_PATTERN.fullmatch(need_id):
            errors.append("metadata cell must declare :id: EXP_####")
        else:
            directory_match = CAPSULE_PATTERN.fullmatch(capsule.name)
            expected = (
                f"EXP_{directory_match.group('number')}" if directory_match else ""
            )
            if need_id != expected:
                errors.append(f"path/id mismatch: expected {expected}, found {need_id}")
        if ":experiment_date:" not in source:
            errors.append("EXP metadata must declare experiment_date")
        if "**Question.**" not in source or "**Conclusion.**" not in source:
            errors.append("EXP content must include Question and Conclusion summaries")
        forbidden_fields = (":experiment_source:", ":experiment_evidence:")
        for field in forbidden_fields:
            if field in source:
                errors.append(f"obsolete EXP metadata field is forbidden: {field}")

    question = notebook.cells[1]
    if question.cell_type != "markdown" or not str(question.source).startswith(
        "## Question\n"
    ):
        errors.append("Question cell must start with '## Question'")
    setup = notebook.cells[2]
    if setup.cell_type != "code" or "hide-input" not in _tags(setup):
        errors.append("Setup must be hidden code")
    conclusion = notebook.cells[-1]
    if conclusion.cell_type != "markdown" or not str(conclusion.source).startswith(
        "## Conclusion\n"
    ):
        errors.append("Conclusion cell must start with '## Conclusion'")

    expected_execution = 1
    if setup.cell_type == "code":
        if setup.execution_count != expected_execution:
            errors.append("Setup must be execution_count 1; recapture linearly")
        expected_execution += 1
    step_number = 1
    for index in range(3, len(notebook.cells) - 1, 2):
        step = notebook.cells[index]
        evidence = notebook.cells[index + 1]
        heading = str(step.source).splitlines()[0] if step.source else ""
        match = STEP_PATTERN.fullmatch(heading)
        if (
            step.cell_type != "markdown"
            or match is None
            or int(match.group("number")) != step_number
        ):
            errors.append(
                f"step {step_number} must start with '## {step_number}. <title>'"
            )
        if evidence.cell_type != "code":
            errors.append(f"step {step_number} evidence must be a code cell")
        else:
            if "hide-input" not in _tags(evidence):
                errors.append(f"step {step_number} evidence must use hide-input")
            if evidence.execution_count != expected_execution:
                errors.append(
                    f"step {step_number} evidence must have execution_count "
                    f"{expected_execution}"
                )
            if not evidence.outputs:
                errors.append(f"step {step_number} has no captured evidence output")
            has_error = any(
                output.get("output_type") == "error" for output in evidence.outputs
            )
            if has_error and "raises-exception" not in _tags(evidence):
                errors.append(f"step {step_number} captured an unmarked error")
        step_number += 1
        expected_execution += 1

    stored = str(notebook.metadata.get("ternforge", {}).get("capsule_digest", ""))
    actual = capsule_digest(capsule, notebook)
    if not stored or stored == "UNSET":
        errors.append("missing captured ternforge.capsule_digest")
    elif stored != actual:
        errors.append(
            "capsule digest is stale; causal source/input/dependency state changed"
        )
    return errors


def validate_capsule(capsule: Path) -> list[str]:
    return [
        *_validate_layout(capsule),
        *_validate_pyproject(capsule),
        *_validate_imports(capsule),
        *_validate_report(capsule),
    ]


def main() -> int:
    capsules = sorted(path for path in EXPERIMENTS_ROOT.glob("exp_*") if path.is_dir())
    if not capsules:
        print("No engineering experiment capsules found.")
        return 1
    failures = 0
    for capsule in capsules:
        errors = validate_capsule(capsule)
        if not errors:
            continue
        failures += 1
        print(f"{capsule.relative_to(ROOT)}:")
        for error in errors:
            print(f"  - {error}")
    if failures:
        return 1
    print(f"Validated {len(capsules)} engineering experiment capsule(s).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
