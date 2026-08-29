"""Sphinx configuration for llm-router documentation."""

from __future__ import annotations

import os
import tomllib
from pathlib import Path

project = "llm-router"
_repo_root = Path(__file__).resolve().parent.parent
with (_repo_root / "pyproject.toml").open("rb") as _pyproject_file:
    release = tomllib.load(_pyproject_file)["project"]["version"]
_source_ref = f"v{release}"
_source_base = "https://github.com/betabitplus/llm-router/blob"

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
html_static_path = ["_static"]
html_css_files = ["traceability.css"]
simplepdf_file_name = "release-dossier.pdf"

needs_render_context = {
    "source_base": _source_base,
    "source_ref": _source_ref,
}
needs_string_links = {
    "gherkin_feature_source": {
        "regex": r"(?P<path>features/.+\.feature)$",
        "link_url": "{{ source_base }}/{{ source_ref }}/{{ path }}",
        "link_name": "{{ path }}",
        "options": ["gherkin_feature"],
    },
    "pytest_module_source": {
        "regex": r"(?P<module>tests(?:\.[A-Za-z0-9_]+)+)$",
        "link_url": (
            "{{ source_base }}/{{ source_ref }}/{{ module | replace('.', '/') }}.py"
        ),
        "link_name": "{{ module | replace('.', '/') }}.py",
        "options": ["classname"],
    },
}

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
