---
name: docs
doc_type: index
description: Repository documentation entry point for API reference and executable examples.
---

# Documentation

The committed documentation surface is intentionally small.

- `api.md` defines the generated public API reference.
- `examples/llm_router/` is the source of truth for runnable user workflows.
- `requirements/` contains the authoritative engineering requirements graph.
- `traceability.rst` renders implementation and verification evidence from that graph.

A traceability build needs current pytest evidence. Generate the gitignored local JUnit
with the same hermetic contract as required CI, then build without executing live examples:

```bash
uv run pytest -c pyproject.toml -n 2 \
    --record-mode=none \
    --block-network \
    --allowed-hosts='localhost,127\\.0\\.0\\.1' \
    --cov-context=test \
    --junitxml=docs/_traceability/local-pytest.xml
uv run sphinx-build -W --keep-going -D plot_gallery=0 -b html docs docs/_build/html
```

The full live gallery uses the same local JUnit prerequisite and additionally requires
configured provider credentials:

```bash
uv run sphinx-build -W --keep-going -b html docs docs/_build/html
```

Required CI performs the same JUnit import automatically before its documentation build.
