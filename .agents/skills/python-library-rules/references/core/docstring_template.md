---
name: docstring-template
description: Template guidance for Python file docstrings. Use when you need short, purposeful file-level docstrings for modules, package boundaries, tests, or workbench scripts.
---

# Python File Docstring Template

## Overview

Use this template for Python file docstrings.

## When To Use

Use this template when writing Python file docstrings for regular modules,
package boundaries, tests, or workbench scripts.

## Coverage

This file covers these Python file types:

- regular modules such as `module.py`
- package files such as `package/__init__.py`
- technical pytest modules under `tests/...`
- workbench scripts under `workbench/...`

It does not define one single template for every Python comment.
Use the section that matches the file type.

## Core Rules (Documentation)

- Follow `references/core/comment_template.md` in full for class, method,
  section, and inline comments when they add real signal.
- Follow `references/core/comment_traceability_pattern.md` when code comments
  and docstrings should mirror architecture docs and boundary intent.
- Keep docs short.

## Core Rules

- keep docstrings short and useful
- explain boundary purpose, not obvious code behavior
- use a short summary line first
- include only sections that add real information
- keep file docstrings compatible with the wider comment system:
  file docstrings explain the boundary role, lower-level comments explain
  invariants and local decisions
- add `Examples` only when usage is not obvious

## Standard Modules

Use this pattern for regular Python modules.

### Sections

Use these sections in this order when they are needed:

1. `Why`
2. `When to use`
3. `How`
4. `Notes`
5. `Examples`

Do not force all sections into every file.

- regular modules often need only `Why`
- `When to use` is optional and should explain import or boundary guidance only
  when that guidance is not obvious
- `How` is optional and should explain key usage shape, placement rule, or
  important constraint only when it adds real signal beyond the summary and
  `Why`
- `Notes` is optional and should hold only the most important caveats,
  invariants, or failure-boundary notes when they matter
- keep `Notes` short; one note is common, but two or a few is fine when they
  add real signal
- add `Examples` only when usage is not obvious
- `__init__.py` files are a special case

### Template

```python
"""<short module summary>.

Why:
    <why this module exists>

When to use:
    <when another module should import or rely on it>

How:
    <key usage shape, placement rule, or important constraint>

Notes:
    <short high-signal caveat, invariant, or boundary note when needed>

Examples:
    <short example if needed>
"""
```

### Example

```python
"""Reusable HTTP retry helpers.

Why:
    Keeps retry policy in one place so callers reuse the same backoff and
    timeout defaults.

When to use:
    Import this module when a service client needs standard retry behavior for
    transient request failures.

How:
    Use `build_retry_session()` instead of defining retry adapters in each
    caller.

Notes:
    Retries are for transient failures only, not caller validation errors.

Examples:
    from http_retry import build_retry_session
    session = build_retry_session()
"""
```

### Smaller Example

```python
"""Provider vocabulary declarations.

Why:
    Keeps the public provider names stable and centralized.
"""
```

## Package `__init__.py`

Use a shorter package docstring for `__init__.py`.

- explain why the package exists
- describe what belongs in this package
- describe what does not belong here when the boundary matters
- add examples only if the package exposes a non-obvious public import surface

### Example

```python
"""Shared test support.

Why:
    Holds reusable test infrastructure shared across multiple projects.

What belongs here:
    Generic setup, replay, and console helpers.

What does not belong here:
    Project-specific builders, assertions, or fixture helpers.
"""
```

## Workbench Script Docstrings

Workbench probes are manual exploratory tools, not the source of truth for
durable behavioral contracts. Keep their docstrings focused on why the probe
exists, what it exercises, and what successful manual observation means.

Use these sections when they add signal:

1. `Why`
2. `Covers`
3. `Checks`
4. `Notes`
5. `Examples`

For automated pytest files, including optional technical E2E tests, use the
ordinary test-file guidance. For durable human-readable behavior, use Gherkin
Living Specifications instead of encoding scenario documentation in Python
module docstrings.

## Quick Choice

- use `Standard Modules` for ordinary `.py` files
- use `Package __init__.py` for package boundary files
- use `Workbench Script Docstrings` for manual workbench probes
