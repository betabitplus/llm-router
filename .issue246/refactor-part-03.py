    """The package exposes the real immutable config lifecycle."""
    config = package.get_config()

    assert isinstance(config, LLMRouterConfig)
    assert package.install_config(config) is config


def test_version_is_available() -> None:
    """The package exposes distribution metadata or its source fallback."""
    assert package.__version__
''',
)

# Standard proof document for the baseline public boundary.
write(
    "docs/llm_router/verification/e2e/public-boundary.md",
    '''---
name: public-boundary-e2e
doc_type: verification
description: E2E proof for the real llm-router public config lifecycle through supported top-level imports.
---

# Public Boundary E2E

## Overview

This slice proves that the existing immutable `LLMRouterConfig` snapshot can be
read, installed, and read back through the supported top-level package API.

## Proof

[test_public_config_pipeline.py](../../../../tests/llm_router/e2e/public_boundary/test_public_config_pipeline.py)
runs the lifecycle through `llm_router` without private imports.

It fails if facade exports, config installation, cache invalidation, or public
snapshot identity drift away from the supported caller contract.
''',
)

# Add the required baseline slice to the e2e docs index without disturbing the
# six product-specific slices.
e2e_index_path = repo / "docs/llm_router/verification/e2e/README.md"
e2e_index = e2e_index_path.read_text(encoding="utf-8")
entry = (
    "- [public-boundary.md](public-boundary.md)\n"
    "  Proves the real public config read/install lifecycle through top-level imports.\n"
)
if "[public-boundary.md]" not in e2e_index:
    marker = "## Files\n\n"
    if marker not in e2e_index:
        raise RuntimeError("Unexpected e2e verification index")
    e2e_index = e2e_index.replace(marker, marker + entry, 1)
e2e_index_path.write_text(e2e_index, encoding="utf-8")

# Workbench modules remain product-owned. Mark every runnable/helper module as
# an IPython cell-compatible module as required by the standard workbench lane.
for path in sorted((repo / "workbench/llm_router").rglob("*.py")):
    if path.name == "__init__.py":
        continue
    text = path.read_text(encoding="utf-8")
    if not text.startswith("# %%"):
        path.write_text("# %%\n" + text, encoding="utf-8")

# Remove stale bytecode produced during local analysis.
for cache in repo.rglob("__pycache__"):
    shutil.rmtree(cache)

# Invariants before handing the tree back to platform checks.
for path in internal.rglob("*.py"):
    text = path.read_text(encoding="utf-8")
    tree = ast.parse(text)
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported = [alias.name for alias in node.names]
        elif isinstance(node, ast.ImportFrom):
            imported = [node.module or ""]
        else:
            continue
        if any(name == "llm_router._api" or name.startswith("llm_router._api.") for name in imported):
            raise RuntimeError(f"private module still imports public facade: {path}")
    if re.search(r"^__all__\s*=", text, re.MULTILINE):
        raise RuntimeError(f"private module still declares __all__: {path}")
for forbidden in (internal / "errors.py", internal / "ids.py", internal / "output.py"):
    if forbidden.exists():
        raise RuntimeError(f"loose private module still exists: {forbidden}")
