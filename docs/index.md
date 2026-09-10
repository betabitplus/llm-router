# llm-router engineering portal

This site is the release-level map of **product intent, engineering learning and
decisions, requirements, executable behavior, implementation, and test evidence**.
You should be able to review the system without opening the repository or an IDE.

::::{grid} 1 2 3 3
:gutter: 3

:::{grid-item-card} ✅ Specification health
:link: specification-health
:link-type: doc

Start with recursive Goal → Feature → Requirement coverage, current required evidence,
and the exact active nodes that block deep coverage.
:::

:::{grid-item-card} 🧭 Requirements hub
:link: requirements/index
:link-type: doc

Start here for product goals, features, accepted product requirements, engineering
constraints, and the relationships between them.
:::

:::{grid-item-card} 🗺️ Requirement maps
:link: requirements/maps
:link-type: doc

Explore a compact Goal → Feature overview, then drill into one product area at a
time. Implementation and test provenance stay out of product maps on purpose.
:::

:::{grid-item-card} 🔬 Engineering experiments
:link: experiments/index
:link-type: doc

See what was tested while an answer was still uncertain, the evidence observed,
and which decision or contract that learning informed.
:::

:::{grid-item-card} 🧠 Architecture decisions
:link: decisions/index
:link-type: doc

Review significant design choices, alternatives, consequences, and supersession
history without turning every implementation detail into an ADR.
:::

:::{grid-item-card} 📖 Executable specifications
:link: specifications
:link-type: doc

Read Gherkin directly on the site. Each feature is followed by its concrete
executed testcase evidence.
:::

:::{grid-item-card} 🧪 Test results
:link: tests
:link-type: doc

Inspect every pytest execution with status, duration, parameters, logs, and rich
attachments such as images, JSON, PDFs, and video.
:::

::::

## Engineering health

{doc}`Specification health <specification-health>` is the canonical coverage view.
It separates structural decomposition, current direct evidence, and recursive deep
coverage instead of combining them into one score. Missing or stale evidence remains
part of the same strict Sphinx-Needs build and is never hidden behind a second graph or
manual dashboard.

## Review from different perspectives

::::{grid} 1 2 3 3
:gutter: 3

:::{grid-item-card} Product perspective
:link: requirements/index
:link-type: doc

**Why and what?** Follow Goal → Feature → Requirement. Engineering constraints are a separate implementation-facing view.
:::

:::{grid-item-card} Experiment perspective
:link: experiments/index
:link-type: doc

**What did we learn before deciding?** Review the question, method, observed evidence, conclusion, and informed artifacts.
:::

:::{grid-item-card} Behavior perspective
:link: specifications
:link-type: doc

**What does the user observe?** Read the executable Gherkin and its executions.
:::

:::{grid-item-card} Verification perspective
:link: tests
:link-type: doc

**What actually ran?** Open each test result and inspect its evidence.
:::

:::{grid-item-card} Decision perspective
:link: decisions/index
:link-type: doc

**Why this design?** Review significant architecture choices, alternatives, consequences, and supersession history.
:::

::::

## Reference and diagnostics

- {doc}`API reference <api>` — public Python API.
- {doc}`Live executable examples <auto_examples/index>` — runnable public workflows.
- {doc}`Specification health <specification-health>` — recursive structure and current-evidence coverage.
- {doc}`Engineering traceability <traceability>` — dense graph and source-centric diagnostic view.
- {doc}`Engineering experiments <experiments/index>` — retained experimental evidence and informed artifacts.
- {doc}`Architecture decisions <decisions/index>` — decision rationale and supersession history.
- {doc}`Verification diagnostics <verification>` — dense JUnit/Sphinx-Needs tables for advanced inspection.
- `needs.json` — machine-readable authoritative graph emitted by the documentation build.
- `release-dossier.pdf` — release PDF emitted by the publication workflow.

```{toctree}
:hidden:
:maxdepth: 3

requirements/index
experiments/index
decisions/index
specifications
tests
api
auto_examples/index
specification-health
traceability
verification
```
