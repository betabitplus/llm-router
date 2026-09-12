---
name: docs
doc_type: index
description: Repository documentation entry point for API reference and executable examples.
---

# Documentation

The committed documentation surface is intentionally small.

- `api.md` defines the generated public API reference.
- `examples/llm_router/` is the source of truth for runnable user workflows.
- `requirements/` contains authoritative Requirements and Technical requirements.
- `experiments/` preserves self-contained Engineering Experiment capsules; each capsule owns its authoritative captured `report/report.ipynb`, and DocOps mounts it directly into Sphinx with execution disabled.
- `decisions/` preserves significant architecture decisions and their rationale.
- `traceability`, `verification`, and `tests` are DocOps-owned generated views over the project graph and retained execution evidence.

A complete local portal build needs the same retained evidence as required CI.
Generate JUnit, Allure results, and coverage.py test contexts from one hermetic pytest
execution, then let DocOps consume those standard artifacts. Documentation builds are
read-only: they do not execute provider examples or Engineering Experiments.

```bash
mkdir -p test-results/allure-results
COVERAGE_FILE=test-results/.coverage uv run pytest -c pyproject.toml -n 2 \
    --record-mode=none \
    --block-network \
    --allowed-hosts='localhost,127\\.0\\.0\\.1' \
    --cov-context=test \
    --junitxml=test-results/pytest-junit.xml \
    --alluredir=test-results/allure-results
COVERAGE_FILE=test-results/.coverage uv run coverage json \
    --show-contexts \
    -o test-results/coverage.json
uv run ternforge-docops build portal \
    --junit test-results/pytest-junit.xml \
    --allure-results test-results/allure-results \
    --coverage test-results/coverage.json
```

Use `uv run ternforge-docops build html` when only the Sphinx/Needs/LLM output is needed.
Required CI produces the same evidence before its documentation build.
