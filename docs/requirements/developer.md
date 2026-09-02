# Developer usability requirements

```{goal} Keep the public library surface and examples safe to consume
:id: GOAL_DEVELOPER_USABILITY

Users should be able to import the documented public API and inspect examples without hidden execution side effects.
```

```{feature} Public package surface
:id: FEAT_PUBLIC_API
:derives: GOAL_DEVELOPER_USABILITY

The package root exposes the supported public API intentionally.
```

```{req} Declared public API resolves from the package root
:id: REQ_PUBLIC_API_SURFACE
:status: accepted
:revision: 1
:required_evidence: impl;unit
:derives: FEAT_PUBLIC_API

**Statement.** Every symbol declared as part of the package public API shall resolve from the package root without requiring callers to import internal modules.

**Rationale.** A coherent package-root surface gives callers a stable import contract and lets internal module organization evolve without becoming public API accidentally.

**Verification intent.** Compare the declared public surface with actual package-root imports and verify each exported symbol resolves without importing private modules directly.
```

```{feature} Executable examples
:id: FEAT_EXECUTABLE_EXAMPLES
:derives: GOAL_DEVELOPER_USABILITY

Examples are import-safe source files that can also be executed by the documentation workflow.
```

```{req} Example imports do not start live network workflows
:id: REQ_EXAMPLE_IMPORT_SAFETY
:status: accepted
:revision: 1
:required_evidence: unit
:derives: FEAT_EXECUTABLE_EXAMPLES

**Statement.** Importing a shipped example module shall not initiate network access or start its live workflow as an import side effect.

**Rationale.** Documentation tooling, IDEs, static analysis, and users may import example modules for inspection; import must therefore remain safe and deterministic.

**Verification intent.** Import every shipped example in an isolated test context and verify the import itself does not initiate its executable workflow or network activity.
```
