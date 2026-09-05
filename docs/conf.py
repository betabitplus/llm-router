"""Sphinx configuration for llm-router documentation."""

from __future__ import annotations

import os
import tomllib
from pathlib import Path

project = "llm-router"
extensions = ["ternforge_docops._api.sphinx_python"]
root_doc = "index"
exclude_patterns = ["_build", "README.md"]

_docs_root = Path(__file__).resolve().parent
_repo_root = _docs_root.parent
with (_repo_root / "pyproject.toml").open("rb") as _pyproject_file:
    release = tomllib.load(_pyproject_file)["project"]["version"]

_source_ref = f"v{release}"
_source_base = "https://github.com/betabitplus/llm-router/blob"
needs_render_context = {
    "source_base": _source_base,
    "source_ref": _source_ref,
}
# Generic source-link mappings and JUnit ingestion are owned by DocOps.

html_static_path = ["_static"]
html_favicon = "_static/gallery/multi-route.svg"

# Required CI stays fully offline. Explicit live documentation builds can opt in
# to external inventories and get links for external APIs used in examples.
intersphinx_mapping = {}
if os.getenv("SPHINX_ENABLE_INTERSPHINX") == "1":
    intersphinx_mapping = {
        "python": ("https://docs.python.org/3/", None),
        "pydantic": ("https://pydantic.dev/docs/validation/latest/", None),
        "pillow": ("https://pillow.readthedocs.io/en/stable/", None),
    }
