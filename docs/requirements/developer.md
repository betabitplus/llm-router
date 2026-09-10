# Developer usability requirements

{doc}`← Intent map <index>` · {doc}`Whole-system map <maps>` · {doc}`Release health <../specification-health>`

Read this page as one continuous branch of the product idea. Start with the local
**Idea branch** for the big picture. Then inspect only the contracts you care about;
under each REQ/TREQ, **Follow this contract to proof** reveals one downstream hop so
you can drill into implementation or executed verification without opening a global
catalogue.

```{goal} Keep the public library surface and examples safe to consume
:id: GOAL_DEVELOPER_USABILITY
:collapse: true

Users should be able to import the documented public API and inspect examples without hidden execution side effects.
```

## Idea branch

This is the whole local intent hierarchy. Use the graph to see the forest; use the
clickable next-level links below it to enter the branch you want.

::::{only} graphviz_available

```{needflow} Developer usability idea branch
:engine: graphviz
:direction: down
:root_id: GOAL_DEVELOPER_USABILITY
:root_direction: incoming
:root_depth: 3
:filter: type in ["goal", "feature", "req", "treq"]
:link_types: derives
:alt: Developer usability from goal through requirements and engineering constraints
```

::::

::::{only} not graphviz_available
The graph renderer is unavailable in this build. The authoritative Goal, Feature,
REQ, and TREQ cards below preserve the same hierarchy through their relationship
links.
::::

### Enter this branch

```{needlist}
:filter: "'GOAL_DEVELOPER_USABILITY' in derives"
```

```{feature} Public package surface
:id: FEAT_PUBLIC_API
:collapse: true
:derives: GOAL_DEVELOPER_USABILITY

The package root exposes the supported public API intentionally.
```

Contracts in this capability:

```{needlist}
:filter: "'FEAT_PUBLIC_API' in derives"
```

```{req} Declared public API resolves from the package root
:id: REQ_PUBLIC_API_SURFACE
:collapse: true
:status: accepted
:revision: 1
:required_evidence: impl;unit
:derives: FEAT_PUBLIC_API

**Statement.** Every symbol declared as part of the package public API shall resolve from the package root without requiring callers to import internal modules.

**Rationale.** A coherent package-root surface gives callers a stable import contract and lets internal module organization evolve without becoming public API accidentally.

**Verification intent.** Compare the declared public surface with actual package-root imports and verify each exported symbol resolves without importing private modules directly.
```

::::{dropdown} Follow this contract to proof

```{needlist}
:filter: "'REQ_PUBLIC_API_SURFACE' in derives or 'REQ_PUBLIC_API_SURFACE' in implements or 'REQ_PUBLIC_API_SURFACE' in verifies"
```

::::

```{feature} Executable examples
:id: FEAT_EXECUTABLE_EXAMPLES
:collapse: true
:derives: GOAL_DEVELOPER_USABILITY

Examples are import-safe source files that can also be executed by the documentation workflow.
```

Contracts in this capability:

```{needlist}
:filter: "'FEAT_EXECUTABLE_EXAMPLES' in derives"
```

```{req} Example imports do not start live network workflows
:id: REQ_EXAMPLE_IMPORT_SAFETY
:collapse: true
:status: accepted
:revision: 1
:required_evidence: unit
:derives: FEAT_EXECUTABLE_EXAMPLES

**Statement.** Importing a shipped example module shall not initiate network access or start its live workflow as an import side effect.

**Rationale.** Documentation tooling, IDEs, static analysis, and users may import example modules for inspection; import must therefore remain safe and deterministic.

**Verification intent.** Import every shipped example in an isolated test context and verify the import itself does not initiate its executable workflow or network activity.
```

::::{dropdown} Follow this contract to proof

```{needlist}
:filter: "'REQ_EXAMPLE_IMPORT_SAFETY' in derives or 'REQ_EXAMPLE_IMPORT_SAFETY' in implements or 'REQ_EXAMPLE_IMPORT_SAFETY' in verifies"
```

::::

## Continue nearby

Do not jump back to an artifact catalogue when this branch raises a neighboring
question. These are the closest semantic continuations:

- {doc}`Configuration predictability <configuration>` — the public configuration API callers use.
- {doc}`Provider portability <providers>` — the stable public contract behind provider changes.
- {doc}`Rich input and output <structured_output>` — representative public workflows and examples.

To zoom all the way out, return to the {doc}`Intent map <index>`. To investigate a release
blocker instead, open {doc}`Specification health <../specification-health>`.
