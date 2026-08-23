"""Sphinx configuration for llm-router documentation."""

from __future__ import annotations

import os
from pathlib import Path

project = "llm-router"

extensions = [
    "myst_parser",
    "sphinx.ext.autodoc",
    "sphinx.ext.autosummary",
    "sphinx.ext.intersphinx",
    "sphinx_gallery.gen_gallery",
    "sphinxcontrib.mermaid",
]

root_doc = "index"
exclude_patterns = ["_build", "README.md"]
myst_fence_as_directive = {"mermaid"}
html_theme = "pydata_sphinx_theme"
html_static_path = ["_static"]

# Required CI stays fully offline. Explicit live documentation builds can opt in
# to external inventories and get links for external APIs used in examples.
intersphinx_mapping = {}
if os.getenv("SPHINX_ENABLE_INTERSPHINX") == "1":
    intersphinx_mapping = {
        "python": ("https://docs.python.org/3/", None),
        "pydantic": ("https://pydantic.dev/docs/validation/latest/", None),
        "pillow": ("https://pillow.readthedocs.io/en/stable/", None),
    }

sphinx_gallery_conf = {
    "examples_dirs": "../examples/llm_router",
    "gallery_dirs": "auto_examples",
    "filename_pattern": r"^(?!.*__init__\.py$).*\.py$",
    "ignore_pattern": r"__init__\.py$",
    "backreferences_dir": "generated/backreferences",
    "doc_module": ("llm_router",),
    "reference_url": {"llm_router": None},
    "copyfile_regex": r".*\.(?:png|pdf|mp4)$",
    "default_thumb_file": str(
        Path(__file__).parent / "_static" / "gallery-default.svg"
    ),
    "junit": "../test-results/sphinx-gallery/junit.xml",
    "remove_config_comments": True,
    "recommender": {
        "enable": True,
        "n_examples": 2,
        "min_df": 1,
        "max_df": 1.0,
    },
}
