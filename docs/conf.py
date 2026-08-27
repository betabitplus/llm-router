"""Sphinx configuration for llm-router documentation."""

from __future__ import annotations

import os

project = "llm-router"

extensions = [
    "myst_parser",
    "sphinx_needs",
    "sphinx_codelinks",
    "sphinxcontrib.test_reports",
    "sphinx.ext.autodoc",
    "sphinx.ext.autosummary",
    "sphinx.ext.intersphinx",
    "sphinx_gallery.gen_gallery",
    "sphinxcontrib.mermaid",
]

root_doc = "index"
needs_from_toml = "../ubproject.toml"
src_trace_config_from_toml = "../ubproject.toml"
tr_extra_options = ["verification_kind", "gherkin_feature", "gherkin_scenario"]
tr_property_link_types = {"verifies": "verifies"}
tr_suite_id_length = 8
tr_case_id_length = 8
exclude_patterns = ["_build", "README.md"]
myst_fence_as_directive = {"mermaid"}
html_theme = "pydata_sphinx_theme"

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
    "filename_pattern": r".*\.py$",
    "backreferences_dir": "generated/backreferences",
    "doc_module": ("llm_router",),
    "reference_url": {"llm_router": None},
    "copyfile_regex": r".*\.(?:png|pdf|mp4)$",
    "junit": "../test-results/sphinx-gallery/junit.xml",
    "remove_config_comments": True,
}
