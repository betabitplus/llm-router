"""Architecture mutants (050): does every import-linter contract catch the edge it forbids?

For each contract of the project's import-linter configuration one forbidden dependency edge is
added, in a copy of the project, as a single import at the end of a module the contract governs:
a forbidden contract gets an import of a module it forbids from one of its source modules; a
protected contract, an import of the protected package from a module outside its allowed
importers; a layers contract, an import of its top layer from its bottom one. The contract must
then be reported broken. A contract that stays kept would let that edge in: the Test Plan's
``architecture.forbidden-edge``, challenged at the level of the rules themselves. No model is
asked, and nothing runs but the linter, which reads imports without executing them.

The pilot's first probe of this kind, for one requirement, is
``probe_invalid_config_architecture_fault``; this generalizes it to every rule.
"""

from __future__ import annotations

import hashlib
import re
import shutil
import subprocess
import tempfile
import tomllib
from pathlib import Path

SCHEMA = "ternforge-architecture-mutants-1"
MARKER = "# ternforge architecture mutant"


def module_file(root: Path, name: str) -> Path | None:
    """The file of a module or package under ``src`` or the project root."""
    parts = [part for part in name.split(".") if part and part != "**" and part != "*"]
    for base in (root / "src", root):
        path = base.joinpath(*parts)
        for candidate in (path / "__init__.py", path.with_suffix(".py")):
            if candidate.is_file():
                return candidate
    return None


def submodule(root: Path, package: str) -> str | None:
    """One module inside a package, for a contract that forbids only a package's submodules."""
    path = module_file(root, package)
    if path is None or path.name != "__init__.py":
        return None
    for child in sorted(path.parent.iterdir()):
        if child.suffix == ".py" and child.name != "__init__.py":
            return f"{package}.{child.stem}"
        if (child / "__init__.py").is_file():
            return f"{package}.{child.name}"
    return None


def edge(root: Path, contract: dict) -> tuple[str, str] | None:
    """The importing module and the imported one of the edge this contract must forbid."""
    kind = contract.get("type")
    if kind == "forbidden":
        source = contract["source_modules"][0]
        forbidden = contract["forbidden_modules"][0]
        if forbidden.endswith(".**") or forbidden.endswith(".*"):
            forbidden = submodule(root, forbidden.rsplit(".", 1)[0]) or ""
        return (source, forbidden) if forbidden else None
    if kind == "protected":
        protected = contract["protected_modules"][0]
        allowed = contract.get("allowed_importers") or []
        root_package = protected.split(".")[0]
        if not any(root_package == item or root_package.startswith(item + ".") for item in allowed):
            return root_package, submodule(root, protected) or protected
        return None
    if kind == "layers":
        container = (contract.get("containers") or [""])[0]
        layers = contract.get("layers") or []
        if len(layers) < 2:
            return None
        top = re.split(r"[:|]", layers[0])[0].strip()
        bottom = re.split(r"[:|]", layers[-1])[0].strip()
        join = (lambda name: f"{container}.{name}" if container else name)
        return join(bottom), join(top)
    return None


def generate(root: Path) -> list[dict]:
    """One mutant per import-linter contract that has an edge to forbid."""
    config = tomllib.loads((root / "pyproject.toml").read_text())
    contracts = ((config.get("tool") or {}).get("importlinter") or {}).get("contracts") or []
    mutants = []
    for contract in contracts:
        found = edge(root, contract)
        path = module_file(root, found[0]) if found else None
        if not found or path is None:
            mutants.append({"contract": contract.get("id"), "name": contract.get("name"), "type": contract.get("type"), "edge": None})
            continue
        importer, imported = found
        mutants.append({
            "id": hashlib.sha256(f"{contract.get('id')}|{importer}|{imported}".encode()).hexdigest()[:16],
            "contract": contract.get("id"), "name": contract.get("name"), "type": contract.get("type"),
            "edge": [importer, imported], "file": str(path.relative_to(root)),
        })
    return mutants


def run(root: Path, mutants: list[dict], lint_imports: Path, timeout: int = 300) -> list[dict]:
    """Run the linter once per mutant in one copy of the project, restoring each file after it."""
    results = []
    with tempfile.TemporaryDirectory(prefix="ternforge-architecture-mutants-") as scratch:
        copy = Path(scratch) / "copy"
        copy.mkdir()
        shutil.copy2(root / "pyproject.toml", copy / "pyproject.toml")
        for name in ("src", "tests", "examples"):
            if (root / name).exists():
                shutil.copytree(root / name, copy / name, ignore=shutil.ignore_patterns("__pycache__", "cassettes", "*.yaml"))
        env = {"PYTHONPATH": f"{copy / 'src'}:{copy}", "PATH": "/usr/bin:/bin", "PYTHONDONTWRITEBYTECODE": "1"}
        for mutant in mutants:
            if not mutant.get("edge"):
                results.append({**mutant, "outcome": "invalid", "reason": "no edge this contract forbids could be built"})
                continue
            target = copy / mutant["file"]
            original = target.read_text()
            try:
                target.write_text(original.rstrip("\n") + f"\nimport {mutant['edge'][1]}  {MARKER}\n")
                done = subprocess.run([str(lint_imports), "--no-cache"], cwd=copy, env=env, text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=timeout, check=False)
                broken = re.search(re.escape(str(mutant["name"])) + r"\s+BROKEN", done.stdout) is not None
                outcome = "caught" if broken else "survived"
                reason = f"{mutant['name']} reports the edge broken" if broken else "the contract stays kept with the edge in"
            finally:
                target.write_text(original)
            results.append({**mutant, "outcome": outcome, "reason": reason})
    return results
