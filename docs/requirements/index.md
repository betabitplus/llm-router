# Requirements hub

The requirements graph is the primary way to understand **why** `llm-router`
exists and how product intent becomes executable behavior. Start with a product
area below, or use the visual maps when you want the whole picture.

::::{grid} 1 2 3 3
:gutter: 3

:::{grid-item-card} Routing reliability
:link: routing
:link-type: doc
:class-card: portal-card

Fallback, route ordering, timeouts, attempt limits, and rate-limit-aware routing.
:::

:::{grid-item-card} Configuration
:link: configuration
:link-type: doc
:class-card: portal-card

Effective settings, credentials, validation, and installed configuration behavior.
:::

:::{grid-item-card} Provider portability
:link: providers
:link-type: doc
:class-card: portal-card

Provider adapters and the normalized public semantics they must preserve.
:::

:::{grid-item-card} Resilience
:link: resilience
:link-type: doc
:class-card: portal-card

Retries, recoverable failures, and reliable execution across provider boundaries.
:::

:::{grid-item-card} Structured output & media
:link: structured_output
:link-type: doc
:class-card: portal-card

Schemas, text, images, documents, video, and multimodal normalization.
:::

:::{grid-item-card} Tool orchestration
:link: tools
:link-type: doc
:class-card: portal-card

Tool selection, execution, multi-round loops, and public tool traces.
:::

:::{grid-item-card} Sessions
:link: sessions
:link-type: doc
:class-card: portal-card

Conversation continuity, persistence, restoration, and forking.
:::

:::{grid-item-card} Data safety
:link: security
:link-type: doc
:class-card: portal-card

Sensitive-data redaction and safe failure/logging behavior.
:::

:::{grid-item-card} Developer usability
:link: developer
:link-type: doc
:class-card: portal-card

Public API coherence, packaging, examples, and developer-facing guarantees.
:::

::::

## Visual perspectives

::::{grid} 1 2 2 2
:gutter: 3

:::{grid-item-card} 🗺️ Requirement maps
:link: maps
:link-type: doc
:class-card: portal-card

See the product hierarchy **Goal → Feature → Requirement**, then drill into
small feature-focused maps. Engineering constraints are shown separately so they
do not masquerade as another layer of product intent.
:::

:::{grid-item-card} 🧪 Executable specifications
:link: ../specifications
:link-type: doc
:class-card: portal-card

Read Gherkin directly on the site and see compact execution summaries immediately
under each feature.
:::

::::

## How to read a requirement

Product requirements use one reviewable structure throughout the portal:

- **Statement** is the normative product contract: what the system shall do.
- **Rationale** explains why the capability matters and helps reviewers detect
  accidental or gold-plated requirements.
- **Verification intent** describes the observable proof expected without
  turning a particular test fixture into the requirement itself.

Engineering constraints use the same structure, but their normative paragraph
is labeled **Constraint** because they describe implementation-facing boundaries
or invariants derived from a product requirement.

### Lifecycle

::::{grid} 1 3 3 3
:gutter: 2

:::{grid-item-card} Accepted
:class-card: portal-card

{need_count}`type in ["req", "treq"] and status == "accepted"` objects form the
current reviewed engineering contract.
:::

:::{grid-item-card} Draft
:class-card: portal-card

{need_count}`type in ["req", "treq"] and status == "draft"` objects are still
under review and must not be mistaken for an accepted contract.
:::

:::{grid-item-card} Deprecated
:class-card: portal-card

{need_count}`type in ["req", "treq"] and status == "deprecated"` objects remain
visible for history and impact analysis but are no longer current intent.
:::

::::

A semantic change to an accepted requirement increments its `revision`. Source
and verification links target that exact revision, so stale evidence is rejected
until it has been reviewed and repinned.

## Requirements catalogue

Every authoritative requirement object is linked below. Use these lists for fast
scanning; open an item for its full text and relationships, or switch to
{doc}`Requirement maps <maps>` for the visual hierarchy.

### Goals

```{needlist}
:filter: type == "goal"
```

### Features

```{needlist}
:filter: type == "feature"
```

### Product requirements

```{needlist}
:filter: type == "req"
```

### Engineering constraints

```{needlist}
:filter: type == "treq"
```

```{toctree}
:hidden:
:maxdepth: 2

maps
routing
configuration
providers
resilience
structured_output
tools
sessions
security
developer
```
