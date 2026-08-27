---
name: docs
doc_type: index
description: Repository documentation entry point for API reference and executable examples.
---

# Documentation

The committed documentation surface is intentionally small.

- `api.md` defines the generated public API reference.
- `examples/llm_router/` is the source of truth for runnable user workflows.
- `index.md` publishes the API reference and the generated Sphinx-Gallery output.

Build without executing live examples:

```bash
uv run sphinx-build -W --keep-going -D plot_gallery=0 -b html docs docs/_build/html
```

Build the full live gallery with configured provider credentials:

```bash
uv run sphinx-build -W --keep-going -b html docs docs/_build/html
```
