"""Sphinx configuration for llm-router documentation."""

from __future__ import annotations

import os
import shutil
import tomllib
from collections.abc import Callable
from pathlib import Path
from typing import Protocol


class _SphinxApp(Protocol):
    outdir: str

    def connect(self, event: str, callback: Callable[..., None]) -> object: ...


project = "llm-router"
_docs_root = Path(__file__).resolve().parent
_repo_root = _docs_root.parent
_experiment_source_root = _repo_root / "experiments" / "llm_router"
_experiment_generated_root = _docs_root / "experiments" / "_generated"
if _experiment_generated_root.exists():
    shutil.rmtree(_experiment_generated_root)
for _capsule in sorted(_experiment_source_root.glob("exp_[0-9][0-9][0-9][0-9]_*/")):
    _report = _capsule / "report" / "report.ipynb"
    if not _report.is_file():
        continue
    _target = _experiment_generated_root / _capsule.name / "report.ipynb"
    _target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(_report, _target)

with (_repo_root / "pyproject.toml").open("rb") as _pyproject_file:
    release = tomllib.load(_pyproject_file)["project"]["version"]
_source_ref = f"v{release}"
_source_base = "https://github.com/betabitplus/llm-router/blob"

extensions = [
    "myst_nb",
    "sphinx_design",
    "sphinx_needs",
    "sphinx_codelinks",
    "sphinxcontrib.test_reports",
    "sphinx_llm.txt",
    "sphinx_simplepdf",
    "sphinx.ext.autodoc",
    "sphinx.ext.autosummary",
    "sphinx.ext.graphviz",
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
exclude_patterns = ["_build", "README.md", "auto_examples/*.ipynb"]
myst_enable_extensions = ["colon_fence"]
myst_fence_as_directive = {"mermaid"}
nb_execution_mode = "off"
nb_code_prompt_show = "Show experiment code"
nb_code_prompt_hide = "Hide experiment code"
html_theme = "pydata_sphinx_theme"
html_static_path = ["_static"]
html_favicon = "_static/gallery/multi-route.svg"
html_css_files = ["traceability.css", "portal.css"]
simplepdf_file_name = "release-dossier.pdf"
graphviz_output_format = "svg"
needs_flow_engine = "graphviz"
needs_flow_direction = "left"
needs_role_need_max_title_length = -1
needs_card_layouts = {
    "portal": {
        "extends": "clean",
        "meta": {
            "fields": "stored",
            "exclude": ["layout", "style"],
        },
    },
}
needs_default_layout = "portal"

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


def _copy_experiment_inputs(app: _SphinxApp, exception: Exception | None) -> None:
    if exception is not None:
        return
    output_root = Path(app.outdir) / "experiments" / "_generated"
    for capsule in sorted(_experiment_source_root.glob("exp_[0-9][0-9][0-9][0-9]_*/")):
        source = capsule / "inputs"
        if not source.is_dir():
            continue
        target = output_root / capsule.name / "inputs"
        shutil.rmtree(target, ignore_errors=True)
        shutil.copytree(source, target)


def setup(app: _SphinxApp) -> None:
    """Register experiment input copying for rendered reports."""
    app.connect("build-finished", _copy_experiment_inputs)
