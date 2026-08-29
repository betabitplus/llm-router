# Tool orchestration requirements

```{goal} Execute local tools through a bounded public orchestration contract
:id: GOAL_TOOL_ORCHESTRATION

Tool-capable provider requests must preserve explicit tool selection, multi-round execution, and safe public failure boundaries.
```

```{feature} Tool selection
:id: FEAT_TOOL_SELECTION
:derives: GOAL_TOOL_ORCHESTRATION

The normalized tool contract can express an explicit tool choice across provider families.
```

```{req} Explicit tool choice is honored
:id: REQ_TOOL_CHOICE
:revision: 1
:needs_artifacts: impl;bdd
:derives: FEAT_TOOL_SELECTION

When the caller explicitly selects a named tool, supported provider routes must request and execute that tool rather than silently choosing another tool.
```

```{feature} Tool execution
:id: FEAT_TOOL_EXECUTION
:derives: GOAL_TOOL_ORCHESTRATION

The router can execute local tools across multiple provider turns while enforcing public error and round-limit boundaries.
```

```{req} Multi-round tool execution
:id: REQ_MULTI_ROUND_TOOL_EXECUTION
:revision: 1
:needs_artifacts: impl;bdd
:derives: FEAT_TOOL_EXECUTION

Supported provider routes must be able to execute a multi-step local-tool workflow and feed tool results back into subsequent provider turns until a final response is produced.
```

```{treq} Tool registry preserves callable contracts
:id: TREQ_TOOL_REGISTRY
:revision: 1
:needs_artifacts: impl;unit
:derives: REQ_MULTI_ROUND_TOOL_EXECUTION

The tool registry must reject duplicate tool names, derive callable schemas that match Python signatures, parse supported provider tool-call shapes, and execute registered callables consistently.
```

```{req} Tool runtime failures are bounded and public
:id: REQ_TOOL_RUNTIME_SAFETY
:revision: 1
:needs_artifacts: impl;bdd
:derives: FEAT_TOOL_EXECUTION

Local tool failures must surface as the public tool-execution error without leaking sensitive arguments, and tool execution must stop at the configured maximum round count.
```
