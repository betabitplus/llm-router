"""Capture one Engineering Experiment report from an isolated capsule copy."""

from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import tempfile
from pathlib import Path

import nbformat
from check_experiment_reports import capsule_digest

ROOT = Path(__file__).resolve().parents[1]
EXPERIMENTS_ROOT = ROOT / "experiments" / "llm_router"
_EXECUTE_NOTEBOOK = """from pathlib import Path
import os
import nbformat
from nbclient import NotebookClient

report = Path("report/report.ipynb")
notebook = nbformat.read(report, as_version=4)
client = NotebookClient(notebook, timeout=1800)
client.execute(cwd=str(report.parent.resolve()), env=os.environ.copy())
nbformat.write(notebook, report)
"""


def _resolve_capsule(value: str) -> Path:
    normalized = value.lower().replace("exp_", "")
    if normalized.isdigit():
        prefix = f"exp_{int(normalized):04d}_"
        matches = sorted(
            path for path in EXPERIMENTS_ROOT.glob(f"{prefix}*") if path.is_dir()
        )
    else:
        candidate = EXPERIMENTS_ROOT / value
        matches = [candidate] if candidate.is_dir() else []
    if len(matches) != 1:
        message = (
            f"Expected exactly one experiment capsule for {value!r}; "
            f"found {len(matches)}"
        )
        raise SystemExit(message)
    return matches[0]


def _copy_capsule(source: Path, destination: Path) -> None:
    shutil.copytree(
        source,
        destination,
        ignore=shutil.ignore_patterns(".venv", "__pycache__", "*.pyc"),
    )


def _execute_report(capsule: Path) -> None:
    command = [
        "uv",
        "run",
        "--locked",
        "--managed-python",
        "--group",
        "report",
        "python",
        "-c",
        _EXECUTE_NOTEBOOK,
    ]
    environment = os.environ.copy()
    environment.pop("PYTHONPATH", None)
    environment.pop("VIRTUAL_ENV", None)
    for name in tuple(environment):
        if name.startswith("DIRENV_"):
            environment.pop(name)
    subprocess.run(command, cwd=capsule, check=True, env=environment)


def capture(capsule: Path) -> None:
    with tempfile.TemporaryDirectory(prefix=f"{capsule.name}-") as temp_dir:
        isolated = Path(temp_dir) / capsule.name
        _copy_capsule(capsule, isolated)
        _execute_report(isolated)

        report_path = isolated / "report" / "report.ipynb"
        notebook = nbformat.read(report_path, as_version=4)
        notebook.metadata.setdefault("ternforge", {})["capsule_digest"] = (
            capsule_digest(
                isolated,
                notebook,
            )
        )
        nbformat.write(notebook, report_path)

        shutil.copy2(report_path, capsule / "report" / "report.ipynb")
        isolated_artifacts = isolated / "artifacts"
        target_artifacts = capsule / "artifacts"
        if isolated_artifacts.is_dir():
            if target_artifacts.exists():
                shutil.rmtree(target_artifacts)
            shutil.copytree(isolated_artifacts, target_artifacts)

    print(f"Captured {capsule.relative_to(ROOT)} from an isolated temporary copy.")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "experiment", help="EXP number (for example 0001) or capsule directory name"
    )
    args = parser.parse_args()
    capture(_resolve_capsule(args.experiment))


if __name__ == "__main__":
    main()
