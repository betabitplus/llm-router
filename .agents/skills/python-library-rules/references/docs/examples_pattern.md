---
name: examples-pattern
description: Reusable live-example rules for Ternforge Python libraries. Use when adding or changing caller-facing runnable examples or generated example documentation.
---

# Examples Pattern

## Contract

`examples/<package>/*.py` is the source of truth for representative caller-facing workflows.
Each example is a complete runnable program built only on the supported public package API.

Keep examples live: when a workflow depends on providers, credentials, files, or external
services, direct execution uses the real dependency. Do not replace live behavior with
mocks, recordings, replay fixtures, canned responses, or example-only stubs.

Put exhaustive provider permutations, failure paths, retries, and technical matrices in
unit/integration/property-based tests. Keep Living Specifications representative of the
durable human-readable contract rather than multiplying user examples.

## Execution Boundary

Keep imports and module initialization safe offline. Put the live workflow behind an ordinary
`main()` entry point and `if __name__ == "__main__":` guard so CI can import the module without
executing external work.

Use Sphinx-Gallery's normal module docstring format. `# %%` cell markers may split the source
for VS Code/IPython/Jupytext-style interactive use; they are an authoring convenience, not a
policy requirement.

## Documentation

Sphinx-Gallery renders the same Python source into HTML, captured output, downloadable Python,
and Jupyter notebooks. Do not duplicate complete walkthrough code in a parallel `usage.md`.
Prefer a real generated figure for the thumbnail. For non-visual examples that need a curated
thumbnail, use a committed per-example `sphinx_gallery_thumbnail_path`; do not add a global
custom fallback only to fill empty gallery cards.

Required CI may lint, type-check, import, and build the gallery with live execution disabled.
Full live execution stays explicit and uses the developer's configured environment.
