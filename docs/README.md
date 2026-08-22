---
name: docs
doc_type: index
description: Repository documentation index. Use when you need the right docs entry point.
---

# Documentation

## Overview

These docs describe the llm router architecture, dependency roles, verification
approach, and generated live-example gallery.

## Files

- [Package Docs](llm_router/README.md)
  Indexes the package documentation.
  Use it to enter the package architecture, examples, dependency, and verification
  docs.

## Live Examples

The source of truth for runnable user workflows is the repository
`examples/llm_router/` tree. [index.md](index.md) defines the generated Sphinx
site that publishes the same source as the live-example gallery.

Build without executing live examples:

```bash
uv run sphinx-build -W --keep-going -D plot_gallery=0 -b html docs docs/_build/html
```

Build the full live gallery with the configured provider credentials:

```bash
uv run sphinx-build -W --keep-going -b html docs docs/_build/html
```

Open `docs/_build/html/index.html` in a browser to inspect the generated site.
