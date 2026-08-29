"""Sphinx configuration for llm-router documentation."""

from __future__ import annotations

import os
from pathlib import Path

project = "llm-router"

extensions = [
    "myst_parser",
    "sphinx_needs",
    "sphinx_codelinks",
    "sphinxcontrib.test_reports",
    "sphinx_llm.txt",
    "sphinx_simplepdf",
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
simplepdf_file_name = "release-dossier.pdf"

local_pytest_junit = Path(__file__).parent / "_traceability" / "local-pytest.xml"
if not local_pytest_junit.is_file():
    exclude_patterns.append("local-pytest-evidence.rst")

sphinx_tags = globals().get("tags")

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

# sphinx-llm runs a dedicated markdown subprocess with this tag. Keep that
# derived build read-only: provider examples execute only in the primary docs build.
if sphinx_tags is not None and sphinx_tags.has("sphinx_llm_markdown"):
    sphinx_gallery_conf["plot_gallery"] = False
