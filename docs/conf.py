"""Sphinx configuration for llm-router documentation."""

from __future__ import annotations

project = "llm-router"

extensions = [
    "myst_parser",
    "sphinx.ext.autodoc",
    "sphinx.ext.autosummary",
    "sphinx_gallery.gen_gallery",
    "sphinxcontrib.mermaid",
]

root_doc = "index"
exclude_patterns = ["_build", "README.md"]
myst_fence_as_directive = {"mermaid"}
html_theme = "pydata_sphinx_theme"

sphinx_gallery_conf = {
    "examples_dirs": "../examples/llm_router",
    "gallery_dirs": "auto_examples",
    "filename_pattern": r"^(?!.*__init__\.py$).*\.py$",
    "ignore_pattern": r"__init__\.py$",
    "backreferences_dir": "generated/backreferences",
    "doc_module": ("llm_router",),
    "reference_url": {"llm_router": None},
    "copyfile_regex": r".*\.(?:png|pdf|mp4)$",
}
