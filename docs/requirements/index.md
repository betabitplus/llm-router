# Intent map

This is the main semantic entry point to `llm-router`. Do not start from a catalogue
of requirements or tests. Start from **why the product exists**, choose one goal, and
follow that branch until you reach the proof you need.

## Request execution and reliability

These goals describe how a request is configured, routed, recovered, and kept
portable across provider families.

::::{grid} 1 2 2 2
:gutter: 3

:::{grid-item-card} Keep requests moving across route failures
:link: routing
:link-type: doc

Fallback, timeouts, route-attempt limits, sticky starting routes, and rate-limit-aware
selection.
:::

:::{grid-item-card} Make effective configuration predictable
:link: configuration
:link-type: doc

Precedence, credentials, validation, installed configuration, and the runtime behavior
that must follow from it.
:::

:::{grid-item-card} Recover from transient failures without unbounded work
:link: resilience
:link-type: doc

Provider retry and structured-output repair, including the lower-level constraints
that keep both recovery loops bounded and deterministic.
:::

:::{grid-item-card} Preserve one public contract across providers
:link: providers
:link-type: doc

Provider portability, asynchronous execution, normalized success responses, usage,
and public provider-error boundaries.
:::

::::

## User capabilities

These goals describe what callers can do through the normalized router contract.

::::{grid} 1 1 3 3
:gutter: 3

:::{grid-item-card} Rich input and structured output
:link: structured_output
:link-type: doc

Structured text, documents, images, video, schema handling, and multimodal content
normalization.
:::

:::{grid-item-card} Local tool orchestration
:link: tools
:link-type: doc

Explicit tool choice, multi-round execution, callable contracts, bounded failures,
and public tool behavior.
:::

:::{grid-item-card} Session continuity
:link: sessions
:link-type: doc

Remembering, isolating, forking, clearing, saving, restoring, and safely serializing
conversation state.
:::

::::

## Trust and usability

These goals constrain how the system can be observed and consumed.

::::{grid} 1 2 2 2
:gutter: 3

:::{grid-item-card} Keep sensitive data out of retained artifacts
:link: security
:link-type: doc

Credentials, request content, tool arguments, runtime diagnostics, and replay evidence
must stay safe to retain.
:::

:::{grid-item-card} Keep the public library safe to consume
:link: developer
:link-type: doc

A coherent package-root API and examples that remain safe to import and inspect.
:::

::::

## How each branch works

Every product-area page follows the same reading pattern:

Goal → Feature → Requirement → optional Engineering Constraint → implementation / executed test

First read the **Idea branch** diagram to see the whole local hierarchy without test
noise. Then read only the contracts that matter to you. Under every REQ and TREQ,
open **Follow this contract to proof** to see exactly one downstream hop. That keeps
each drill-down small while still letting you walk all the way to implementation and
test evidence.

If you want to change direction, use **Continue nearby** at the bottom of the branch
instead of returning to a global catalogue.

## Whole product at a glance

The {doc}`Whole-system intent map <maps>` shows only Goals and Features so you can
reorient without losing the forest in implementation or test nodes.

::::{dropdown} Reference: lifecycle and complete object catalogues

**Accepted** requirements and engineering constraints are the current reviewed
contract. **Draft** items are still under review. **Deprecated** items remain visible
for history and impact analysis but are not current obligations.

A semantic change to an accepted requirement increments its `revision`. Source and
verification links target that exact revision, so stale evidence is rejected until it
has been reviewed and repinned.

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

::::

```{toctree}
:hidden:
:maxdepth: 2

maps
routing
configuration
resilience
providers
structured_output
tools
sessions
security
developer
```
