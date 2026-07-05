#!/usr/bin/env python3
from __future__ import annotations

import shutil
import sys
from pathlib import Path

ARCH_DOC = '---\nname: public-boundary-and-errors\ndoc_type: architecture\ndescription: Stable output and error boundaries exposed by llm_router.\n---\n\n# Public Boundary And Errors\n\nThe public package returns provider-neutral `LLMRouterResponse` values and raises\nexceptions from the `LLMRouterError` hierarchy. Provider SDK objects, transport\nexceptions, raw payloads, and implementation-only state stay behind the private\nimplementation boundary.\n\nThe detailed product semantics are documented in\n[Public Output And Errors](public-output-and-errors.md). Shared bounded preview\nand structured logging primitives come directly from `py-lib-runtime`; the\npackage retains only its product-specific error taxonomy and event vocabulary.\n'
VERIFICATION_DOC = '---\nname: public-boundary-and-errors-verification\ndoc_type: verification\ndescription: Verification of the stable llm_router output and error boundary.\n---\n\n# Public Boundary And Errors Verification\n\nThe public boundary is protected by unit, integration, property, installed\nartifact, public API, and end-to-end checks. The\n[`public-output-and-errors`](e2e/public-output-and-errors.md) slice proves\nresponse normalization, provider error translation, tool failures, and tool\nround limits through the supported top-level package API.\n\n`py-lib-check-public-contract-boundary`, import-linter contracts, and the\ninstalled-artifact smoke tests additionally prevent private implementation\nmodules from becoming caller dependencies.\n'

repo = Path(sys.argv[1]).resolve()
reference = Path(sys.argv[2]).resolve()


def replace_tree(name: str) -> None:
    target = repo / name
    if target.exists():
        shutil.rmtree(target)
    shutil.copytree(reference / name, target)


# Template-owned repository shell. The temporary project workflow is retained
# only until this migration process commits and pushes the finished tree.
bootstrap = repo / ".github/workflows/project-issue-246-bootstrap.yml"
bootstrap_text = bootstrap.read_text() if bootstrap.exists() else None
for directory in (".agents", ".devcontainer", ".vscode", "scripts"):
    replace_tree(directory)
replace_tree(".github")
if bootstrap_text is not None:
    bootstrap.parent.mkdir(parents=True, exist_ok=True)
    bootstrap.write_text(bootstrap_text)

for name in (
    ".editorconfig",
    ".envrc",
    ".gitignore",
    ".gitleaks.toml",
    ".markdown-link-check.json",
    ".markdownlint.yaml",
    ".mdformat.toml",
    ".pre-commit-config.yaml",
    "AGENTS.md",
    "CONTRIBUTING.md",
    "LICENSE",
    "MANIFEST.in",
    "RTK.md",
    "SETUP.md",
    "renovate.json5",
    "typos.toml",
):
    shutil.copy2(reference / name, repo / name)

for obsolete in (".flake8", ".github/dependabot.yml"):
    path = repo / obsolete
    if path.is_file() or path.is_symlink():
        path.unlink()
    elif path.exists():
        shutil.rmtree(path)

# Keep product-owned package, tests, documentation, workbench, README, and
# changelog. Adopt only the standard roots around those product trees.
shutil.copy2(reference / "docs/README.md", repo / "docs/README.md")
shutil.copy2(reference / "tests/README.md", repo / "tests/README.md")
shutil.copy2(reference / "tests/__init__.py", repo / "tests/__init__.py")
shutil.copy2(reference / "tests/conftest.py", repo / "tests/conftest.py")
shutil.copy2(reference / "workbench/__init__.py", repo / "workbench/__init__.py")
(repo / "examples/llm_router").mkdir(parents=True, exist_ok=True)
shutil.copy2(reference / "examples/__init__.py", repo / "examples/__init__.py")
shutil.copy2(
    reference / "examples/llm_router/__init__.py",
    repo / "examples/llm_router/__init__.py",
)
for child in (repo / "examples/llm_router").iterdir():
    if child.name != "__init__.py":
        if child.is_dir():
            shutil.rmtree(child)
        else:
            child.unlink()

# `pyproject.toml` and `_copier_answers.yml` were committed first so their
# provenance and project dependency reconciliation remain reviewable.
if not (repo / "pyproject.toml").is_file():
    raise RuntimeError("Missing reconciled pyproject.toml")
if not (repo / "_copier_answers.yml").is_file():
    raise RuntimeError("Missing Copier provenance")

# Remove superseded local shared infrastructure. The product-specific support
# package under tests/llm_router remains authoritative for llm-router behavior.
for obsolete in (
    repo / "src/llm_router/_support",
    repo / "tests/support",
):
    if obsolete.exists():
        shutil.rmtree(obsolete)

# Migrate every applicable product/test/workbench caller directly to public
# py-lib-runtime and py-lib-tooling APIs.
module_replacements = {
    "from llm_router._support.error_formatting import": "from py_lib_runtime import",
    "from llm_router._support.logging import": "from py_lib_runtime import",
    "from tests.support._vcr_shared import": "from py_lib_tooling import",
    "from tests.support.console import": "from py_lib_tooling import",
    "from tests.support.e2e_vcr_guard import": "from py_lib_tooling import",
    "from tests.support.paths import": "from py_lib_tooling import",
    "from tests.support.setup import": "from py_lib_tooling import",
    "from tests.support.vcr_matchers import": "from py_lib_tooling import",
}
for root_name in ("src", "tests", "workbench", "examples"):
    root = repo / root_name
    if not root.exists():
        continue
    for path in root.rglob("*.py"):
        text = path.read_text()
        for old, new in module_replacements.items():
            text = text.replace(old, new)
        path.write_text(text)

retry_path = repo / "src/llm_router/_internal/providers/retry.py"
retry_text = retry_path.read_text()
needle = "before_sleep=build_retry_before_sleep_logger(\n            logger,\n"
replacement = (
    "before_sleep=build_retry_before_sleep_logger(\n"
    "            logger,\n"
    "            event_type=\"llm_router.provider.retry.scheduled\",\n"
)
if retry_text.count(needle) != 2:
    raise RuntimeError("Unexpected provider retry callback shape")
retry_path.write_text(retry_text.replace(needle, replacement))

executor_path = repo / "src/llm_router/_internal/runtime/executor.py"
executor_text = executor_path.read_text()
needle = "logger,\n                    error=exc,\n                    context=_retry_context(request),"
replacement = (
    "logger,\n"
    "                    error=exc,\n"
    "                    event_type=\"llm_router.provider.retry.exhausted\",\n"
    "                    context=_retry_context(request),"
)
if executor_text.count(needle) != 2:
    raise RuntimeError("Unexpected retry exhaustion logging shape")
executor_path.write_text(executor_text.replace(needle, replacement))

# Product documentation for the standard public-contract slice and runtime
# ownership. Existing product semantics remain unchanged.
arch = repo / "docs/llm_router/architecture/concepts/public-boundary-and-errors.md"
arch.parent.mkdir(parents=True, exist_ok=True)
arch.write_text(ARCH_DOC)
verification = repo / "docs/llm_router/verification/public-boundary-and-errors.md"
verification.parent.mkdir(parents=True, exist_ok=True)
verification.write_text(VERIFICATION_DOC)

deps_path = repo / "docs/llm_router/dependencies.md"
deps = deps_path.read_text()
deps = deps.replace('B --> B3["structlog"]', 'B --> B3["py-lib-runtime"]')
deps = deps.replace(
    "| `structlog` | Powers the shared structured logging layer used across config, routing, and provider execution.                | Foundational |",
    "| `py-lib-runtime` | Supplies the authoritative logging, bounded preview, retry-event, and shared runtime primitives used by the package. | Foundational |",
)
deps_path.write_text(deps)

verification_readme = repo / "docs/llm_router/verification/README.md"
text = verification_readme.read_text()
entry = (
    "- [public-boundary-and-errors.md](public-boundary-and-errors.md)\n"
    "  Describes the checks that protect the installed public output and error boundary.\n"
    "  Use it when changing response normalization or public exception translation.\n"
)
if entry not in text:
    marker = "## Files\n\n"
    if marker not in text:
        raise RuntimeError("Unexpected verification README shape")
    text = text.replace(marker, marker + entry, 1)
verification_readme.write_text(text)

text_replacements = {
    "tests/llm_router/e2e/README.md": {
        "- `tests/support/`\n- `tests/llm_router/support/`":
        "- `py_lib_tooling` for repository-agnostic support\n- `tests/llm_router/support/` for product-specific support",
    },
    "tests/llm_router/support/__init__.py": {
        "Cross-project infrastructure that should live in `tests.support`.":
        "Cross-project infrastructure that is provided by `py_lib_tooling`.",
    },
    "tests/llm_router/support/_vcr_body_matching.py": {
        "logic out of the shared `tests.support` layer.":
        "logic out of the shared `py_lib_tooling` package.",
    },
    "tests/llm_router/support/runtime.py": {
        "reusable support under `tests/support/` should not know LLMRouter APIs.":
        "shared `py_lib_tooling` support must not depend on LLMRouter APIs.",
    },
}
for relative, replacements in text_replacements.items():
    path = repo / relative
    text = path.read_text()
    for old, new in replacements.items():
        if old not in text:
            raise RuntimeError(f"Missing expected text in {relative}: {old}")
        text = text.replace(old, new)
    path.write_text(text)
