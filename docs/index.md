# llm-router engineering portal

This site is the release-level map of **product intent, engineering learning and
decisions, requirements, executable behavior, implementation, and test evidence**.
You should be able to review the system without opening the repository or an IDE.

::::{grid} 1 2 3 3
:gutter: 3

:::{grid-item-card} 🧭 Requirements hub
:link: requirements/index
:link-type: doc
:class-card: portal-card

Start here for product goals, features, accepted product requirements, engineering
constraints, and the relationships between them.
:::

:::{grid-item-card} 🗺️ Requirement maps
:link: requirements/maps
:link-type: doc
:class-card: portal-card

Explore a compact Goal → Feature overview, then drill into one product area at a
time. Implementation and test provenance stay out of product maps on purpose.
:::

:::{grid-item-card} 🔬 Engineering experiments
:link: experiments/index
:link-type: doc
:class-card: portal-card

See what was tested while an answer was still uncertain, the evidence observed,
and which decision or contract that learning informed.
:::

:::{grid-item-card} 🧠 Architecture decisions
:link: decisions/index
:link-type: doc
:class-card: portal-card

Review significant design choices, alternatives, consequences, and supersession
history without turning every implementation detail into an ADR.
:::

:::{grid-item-card} 📖 Executable specifications
:link: specifications
:link-type: doc
:class-card: portal-card

Read Gherkin directly on the site. Each feature is followed by its concrete
executed testcase evidence.
:::

:::{grid-item-card} 🧪 Test results
:link: tests
:link-type: doc
:class-card: portal-card

Inspect every pytest execution with status, duration, parameters, logs, and rich
attachments such as images, JSON, PDFs, and video.
:::

::::

## Engineering health

The portal starts with release health before detailed traceability. A successful
strict documentation build means the declared evidence laws and revision-pinned
links are satisfied; the cards below show the current graph and execution state.

::::{grid} 1 2 4 4
:gutter: 2

:::{grid-item-card} Product contract
:class-card: portal-card

{need_count}`type == "req" and status == "accepted"` accepted product requirements
:::

:::{grid-item-card} Engineering constraints
:class-card: portal-card

{need_count}`type == "treq" and status == "accepted"` accepted constraints
:::

:::{grid-item-card} Verification
:class-card: portal-card

{need_count}`type == "testcase" and result == "passed"` / {need_count}`type == "testcase"` executions passing
:::

:::{grid-item-card} Implementation provenance
:class-card: portal-card

{need_count}`type == "impl"` source-linked implementation slices
:::

::::

Missing, unwanted, stale, or non-passing declared evidence fails the same strict
Sphinx-Needs build that produces this portal; it is not hidden behind a separate
manual review dashboard.

## Review from different perspectives

::::{grid} 1 2 3 3
:gutter: 3

:::{grid-item-card} Product perspective
:link: requirements/index
:link-type: doc
:class-card: portal-card

**Why and what?** Follow Goal → Feature → Requirement. Engineering constraints are a separate implementation-facing view.
:::

:::{grid-item-card} Experiment perspective
:link: experiments/index
:link-type: doc
:class-card: portal-card

**What did we learn before deciding?** Review the question, method, observed evidence, conclusion, and informed artifacts.
:::

:::{grid-item-card} Behavior perspective
:link: specifications
:link-type: doc
:class-card: portal-card

**What does the user observe?** Read the executable Gherkin and its executions.
:::

:::{grid-item-card} Verification perspective
:link: tests
:link-type: doc
:class-card: portal-card

**What actually ran?** Open each test result and inspect its evidence.
:::

:::{grid-item-card} Decision perspective
:link: decisions/index
:link-type: doc
:class-card: portal-card

**Why this design?** Review significant architecture choices, alternatives, consequences, and supersession history.
:::

::::

## Reference and diagnostics

- {doc}`API reference <api>` — public Python API.
- {doc}`Live executable examples <auto_examples/index>` — runnable public workflows.
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
traceability
verification
```
