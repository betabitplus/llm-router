# llm-router engineering portal

This portal is meant to be **read as a connected model of the system**, not as a
collection of reports. Pick the route that matches the question you have and stay
on that route until you have enough evidence.

## Three ways through the system

::::{grid} 1 1 3 3
:gutter: 3

:::{grid-item-card} 1. Read the product end to end
:link: traceability-reader
:link-type: doc

**Start here most of the time.** Follow the numbered staircase from goal
to capability to requirement to technical requirement. Implementation and verification
stay inside the contract they prove, while the collapsible sidebar jumps between
goals and capabilities. IDs and concrete test records remain secondary.
:::

:::{grid-item-card} 2. Follow a relationship or change
:link: requirements/maps
:link-type: doc

Start from the whole intent map or a known idea. Move up to the intent that caused
it, down to the contracts it creates, or sideways through the nearby idea links on
each product branch. Use dense traceability only when you need forensic detail.
:::

:::{grid-item-card} 3. See verification health at a glance
:link: verification-health-map
:link-type: doc

Use the Verification Health Map to see where verification fails, layer by layer.
Beside each layer's health it shows how deep, how realistic and how strong the
evidence is, and every mark leads to the contract's evidence when you need details.
:::

::::

## The normal reading direction

Goal → Capability → Requirement → Technical requirement → Implementation / Verification

You do not need to visit every page type. The normal review is:

1. choose a goal in the {doc}`Intent map <requirements/index>`;
2. read that product branch from top to bottom;
3. expand proof only for the Requirement/Technical requirement you want to inspect;
4. open the implementation or executed test node when you need concrete evidence;
5. return through the same relationships or switch to one of the nearby ideas shown
   on the branch page.

This mirrors the authoritative graph. The portal does not maintain a second
navigation model just for presentation.

## Supporting context, when you need it

::::{grid} 1 2 2 2
:gutter: 3

:::{grid-item-card} Architecture decisions
:link: decisions/index
:link-type: doc

Why a durable design choice was made, what alternatives were rejected, and which
contracts or implementation slices it affects.
:::

:::{grid-item-card} Engineering experiments
:link: experiments/index
:link-type: doc

What was learned before a requirement or architecture decision became authoritative.
Experiments provide rationale, never verification.
:::

:::{grid-item-card} Test plan
:link: test-plan
:link-type: doc

Project-wide Test Strategy, reusable Test Models, environment classifications,
completion criteria, evidence gates, and tailoring rules. Requirement-specific
verification profiles reference this policy instead of cloning it.
:::

:::{grid-item-card} Verification profiles
:link: verification-profiles/index
:link-type: doc

Requirement-specific verification design: which criteria are required, where they are exercised,
and which fault checks are blocking. Profiles reference normative contracts instead of defining them.
:::

:::{grid-item-card} Executable specifications
:link: specifications
:link-type: doc

Human-readable Gherkin behavior and its concrete executions. Use this when the
public behavior itself is what you want to inspect.
:::

:::{grid-item-card} API and runnable examples
:link: api
:link-type: doc

The public Python surface and practical workflows. These are usage references, not
the primary engineering-control path.
:::

::::

## Assurance design

::::{grid} 1 1 2 2
:gutter: 3

:::{grid-item-card} Upper-level assurance profiles
:link: assurance-profiles/index
:link-type: doc

Feature, Goal, and Product/System integration and validation Targets. These profiles
add only cross-contract or intended-use evidence that cannot be reduced to one
Requirement/TREQ Verification Profile.
:::

:::{grid-item-card} Contract verification profiles
:link: verification-profiles/index
:link-type: doc

Requirement/TREQ verification Targets: criteria, levels, boundaries, representation,
fault applicability, and blocking contract-level evidence.
:::

::::

## Advanced diagnostics

The pages below deliberately expose dense global data. They are useful for audits
and debugging, but they are **not required stops** in the normal semantic flow.

- {doc}`Engineering traceability <traceability>` — dense cross-graph/source diagnostics.
- {doc}`Verification diagnostics <verification>` — requirement/evidence matrix for forensic inspection.
- {doc}`Raw test results <tests>` — every pytest execution and attachment.
- `needs.json` — machine-readable authoritative Sphinx-Needs graph.
- `release-dossier.pdf` — release PDF produced by the publication workflow.

```{toctree}
:hidden:
:maxdepth: 3

requirements/index
traceability-reader
verification-health-map
experiments/index
decisions/index
specifications
api
auto_examples/index
traceability
test-plan
verification-profiles/index
assurance-profiles/index
verification
evidence-producers
tests
```
