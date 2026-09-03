---
name: docs
doc_type: index
description: Repository documentation entry point for API reference and executable examples.
---

# Documentation

The committed documentation surface is intentionally small.

- `api.md` defines the generated public API reference.
- `examples/llm_router/` is the source of truth for runnable user workflows.
- `requirements/` contains authoritative product requirements and engineering constraints.
- `experiments/` preserves self-contained Engineering Experiment capsules; each capsule owns its authoritative captured `report/report.ipynb`, and DocOps mounts it directly into Sphinx with execution disabled.
- `decisions/` preserves significant architecture decisions and their rationale.
- `traceability.rst` renders the combined Sphinx-Needs graph and its implementation and verification evidence.

A complete local portal build needs current pytest evidence. Generate JUnit and Allure
from the same hermetic test run, then let DocOps consume those artifacts. Documentation
builds are read-only: they do not execute provider examples or Engineering Experiments.

```bash
uv run pytest -c pyproject.toml -n 2 \
    --record-mode=none \
    --block-network \
    --allowed-hosts='localhost,127\\.0\\.0\\.1' \
    --cov-context=test \
    --junitxml=docs/_traceability/local-pytest.xml \
    --alluredir=allure-results
uv run ternforge-docops build portal --allure-results allure-results
```

Use `uv run ternforge-docops build html` when only the Sphinx/Needs/LLM output is needed.
Required CI produces the same evidence before its documentation build.
