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
:status: accepted
:revision: 1
:required_evidence: impl;bdd
:derives: FEAT_TOOL_SELECTION

**Statement.** When the caller explicitly selects a named tool, a supported provider route shall request and execute that tool rather than silently choosing another registered tool.

**Rationale.** Explicit tool choice is caller intent; silently substituting another tool can change side effects and invalidate the meaning of the request.

**Verification intent.** Execute a public tool-capable request with multiple registered tools and an explicit selection, then verify the selected tool is the one requested and executed.
```

```{feature} Tool execution
:id: FEAT_TOOL_EXECUTION
:derives: GOAL_TOOL_ORCHESTRATION

The router can execute local tools across multiple provider turns while enforcing public error and round-limit boundaries.
```

```{req} Multi-round tool execution
:id: REQ_MULTI_ROUND_TOOL_EXECUTION
:status: accepted
:revision: 1
:required_evidence: impl;bdd
:derives: FEAT_TOOL_EXECUTION

**Statement.** Supported provider routes shall be able to execute a multi-step local-tool workflow and feed tool results back into subsequent provider turns until a final response is produced.

**Rationale.** Useful tool orchestration often requires the model to consume one tool result before deciding the next action; a single-round contract would not preserve this workflow.

**Verification intent.** Execute a representative multi-round workflow through the public router and verify each requested tool is executed, its result is returned to the provider turn, and the workflow terminates with the expected final response.
```

```{treq} Tool registry preserves callable contracts
:id: TREQ_TOOL_REGISTRY
:status: accepted
:revision: 1
:required_evidence: impl;unit
:derives: REQ_MULTI_ROUND_TOOL_EXECUTION

**Constraint.** The tool registry shall reject duplicate tool names, derive callable schemas that match Python signatures, parse supported provider tool-call shapes, and execute registered callables consistently.

**Rationale.** The registry is the translation boundary between Python callables and provider tool schemas; ambiguity or schema drift there can invoke the wrong arguments or callable.

**Verification intent.** Directly verify duplicate-name rejection, schema derivation, supported tool-call parsing, and callable execution across representative signatures and provider shapes.
```

```{req} Tool runtime failures are bounded and public
:id: REQ_TOOL_RUNTIME_SAFETY
:status: accepted
:revision: 1
:required_evidence: impl;bdd
:derives: FEAT_TOOL_EXECUTION

**Statement.** Local tool failures shall surface as the public tool-execution error without leaking sensitive arguments, and tool execution shall stop at the configured maximum round count.

**Rationale.** Tool orchestration runs local code with caller data, so failures need a stable public boundary and execution must remain finite even when the provider repeatedly requests tools.

**Verification intent.** Trigger public tool failures containing sensitive arguments and a workflow that exceeds the configured round limit; verify the public error surface, absence of protected argument values, and bounded execution count.
```
