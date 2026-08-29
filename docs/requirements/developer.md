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
:revision: 1
:needs_artifacts: impl;unit
:derives: FEAT_PUBLIC_API

Every symbol declared as part of the package public API must resolve from the package root without requiring callers to import internal modules.
```

```{feature} Executable examples
:id: FEAT_EXECUTABLE_EXAMPLES
:derives: GOAL_DEVELOPER_USABILITY

Examples are import-safe source files that can also be executed by the documentation workflow.
```

```{req} Example imports do not start live network workflows
:id: REQ_EXAMPLE_IMPORT_SAFETY
:revision: 1
:needs_artifacts: unit
:derives: FEAT_EXECUTABLE_EXAMPLES

Importing any shipped example module must not initiate network access or start its live workflow as an import side effect.
```
