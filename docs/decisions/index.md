# Architecture decisions

Architecture Decision Records (ADRs) preserve the reasoning behind significant
engineering choices. They live in the same Sphinx-Needs graph as requirements,
constraints, implementation, and verification evidence, but they are **not**
requirements and do not create verification obligations by themselves.

Write an ADR when a choice is consequential, has credible alternatives, and a
future engineer is likely to ask why the system was shaped this way. Do not write
ADRs for routine refactors, dependency bumps, naming choices, or facts already
expressed as requirements or engineering constraints.

## Decision lifecycle

::::{grid} 1 2 3 3
:gutter: 2

:::{grid-item-card} Accepted
:class-card: portal-card

{need_count}`type == "adr" and status == "accepted"` current decisions
:::

:::{grid-item-card} Proposed
:class-card: portal-card

{need_count}`type == "adr" and status == "proposed"` decisions under review
:::

:::{grid-item-card} Superseded
:class-card: portal-card

{need_count}`type == "adr" and status == "superseded"` historical decisions replaced by newer ADRs
:::

::::

ADR states are `proposed`, `accepted`, `rejected`, `deprecated`, and
`superseded`. A superseded ADR remains in the graph. Its replacement is a new
accepted ADR with a `supersedes` link; accepted replacements may supersede only
records already marked `superseded`.

## Decision log

```{needtable} Architecture decision log
:columns: id;title;status;decision_date;informs_back
:style: table
:filter: type == "adr"
:sort: id
```

## Minimal record

Each ADR requires four content sections:

```text
Context
Decision
Consequences
Alternatives considered
```

Metadata stays deliberately small: stable `ADR_####` ID, lifecycle `status`,
`decision_date`, and optional `affects` / `supersedes` links. ADRs do not use
`revision` or `required_evidence`.

Use `affects` only when a decision materially shapes an existing Feature,
Requirement, Engineering Constraint, or implementation artifact. An Engineering
Experiment may point to the ADR with `informs` when observed evidence materially
contributed to the choice. If a decision creates an enforceable engineering
invariant, express that invariant as an Engineering Constraint and link the ADR to
it; tests verify the constraint, not the ADR.

## Tooling and validation

The ADR format has no separate parser or metadata store:

- **Sphinx-Needs schema validation** checks ADR IDs, lifecycle, date format,
  required sections, allowed link targets, and supersession graph laws. Strict
  Sphinx builds fail on violations and emit `schema_violations.json` for
  machine-readable QA.
- **ubCode** reads the same `ubproject.toml` and schema for live editor
  diagnostics, references, navigation, and impact analysis. Where the `ubc` CLI
  is installed, `ubc check docs/decisions` provides the same fast project lint
  surface without becoming authoritative.
- **markdownlint** and **mdformat** remain the repository's Markdown style and
  formatting gates.
- `needs.json` is the machine-readable decision graph; no separate ADR index or
  database is generated.

For complete local presentation, first produce the project test evidence and then
build the engineering portal with `uv run ternforge-docops build portal --allure-results allure-results`. DocOps consumes existing evidence and runs the
strict Sphinx graph build; it never executes the project test suite itself.

```{toctree}
:hidden:
:maxdepth: 1

0001-provider-adapters-own-provider-protocols
0002-separate-provider-retry-from-route-fallback
```
