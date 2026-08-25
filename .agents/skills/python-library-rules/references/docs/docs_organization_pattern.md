---
name: docs-organization-pattern
description: Reusable project docs organization patterns. Use when you need to shape a project docs tree, choose folder boundaries, or decide how architecture docs should be grouped.
---

# Docs Organization Pattern

## Overview

Use this guide for organizing project documentation trees in a way that stays
readable as the docs set grows.

## When To Use

Use this guide when creating or restructuring a `docs/` tree and the main
question is how the folders and top-level docs should be grouped.

Use this guide when the project needs a stable documentation shape that helps a
reader find the right document quickly.

## Core Patterns

### Top-Level Package Docs Pattern

At the package-doc level, keep a small set of top-level documents for the
questions that cut across the whole package.

Common useful top-level docs are:

- `examples/`
  complete runnable public API workflows
- `dependencies.md`
  runtime dependency justification
- `architecture/`
  product architecture structure
- `verification/`
  proof and validation surfaces

### Semantic Grouping Pattern

Group docs by the question the reader is trying to answer, not by a generic
document type label.

Good group names are familiar and low-friction:

- `principles/`
  durable refactor and review rules for private architecture boundaries
- `concepts/`
  durable architecture ideas and boundaries
- `flows/`
  end-to-end runtime behavior
- `verification/`
  what tests or probes prove

### Scale Pattern

Do not create a subgroup for one file unless the structure itself adds real
meaning.

Add a subgroup when:

- multiple docs clearly share the same reading purpose
- the new folder makes navigation easier
- the split reduces mixed semantics inside one bucket

### Navigation Pattern

Use `README.md` as the index for each docs folder.
Use `index_doc_template.md` for the index file shape.

### Architecture Pattern

For architecture docs, a common useful shape is:

```text
architecture/
├── README.md
├── system.md
├── principles/
├── concepts/
└── flows/
```

Use this only when each subgroup has enough docs to justify the split.

Focused docs should deepen `system.md`, not retell it from another angle.

If `system.md` becomes too broad, move detail into focused docs such as
`principles/`, `concepts/`, or `flows/` instead of adding
another top-level overview doc.

Use `principles/` when the architecture set needs durable refactor or review
rules grounded in the product's own design vocabulary: ownership, layering,
state placement, dependency direction, or adapter boundaries.

Use `concepts/` when readers need focused docs for what the runtime model
means: public nouns, configuration resolution, routing semantics, continuity,
or provider abstraction.

If the library or app is best understood through stable vertical slices, let
`concepts/` define that primary architecture taxonomy. When those slices are
behavioral contracts, use the same vocabulary in Living Specifications under
`features/` rather than mirroring them into handwritten verification/E2E docs.

Do not create `principles/` for generic software design notes that are not
specific to the product's own design, domain, and boundary vocabulary.

Example:

```text
architecture/
├── README.md
├── system.md
├── principles/
│   ├── README.md
│   ├── solid.md
│   └── state-ownership.md
├── concepts/
│   ├── README.md
│   ├── capability-model.md
│   ├── policy-resolution.md
│   ├── state-management.md
│   └── operation-modes.md
├── flows/
│   ├── README.md
│   ├── request-flow.md
│   └── state-flow.md
```

### Verification Pattern

Keep handwritten verification docs for technical verification strategy and
operator/developer guidance that is not already expressed by executable
behavioral specifications.

A compact shape is usually enough:

```text
verification/
├── README.md
├── property-based-testing.md
└── workbench.md
```

When `features/` exists, Living Specifications are the human-readable source of
truth for durable behavior and are published from that source. Do not create a
parallel handwritten E2E taxonomy that repeats scenarios, evidence, or
behavioral guarantees already present in specifications.
