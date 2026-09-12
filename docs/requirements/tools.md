# Tool orchestration requirements

{doc}`← Intent map <index>` · {doc}`Whole-system map <maps>` · {doc}`Release health <../specification-health>`

Read this page as one continuous branch of the product idea. Start with the local
**Idea branch** for the big picture. Then inspect only the contracts you care about;
under each Requirement/Technical requirement, **Follow this contract to proof** reveals one downstream hop so
you can drill into implementation or executed verification without opening a global
catalogue.

```{goal} Execute local tools through a bounded public orchestration contract
:id: GOAL_TOOL_ORCHESTRATION
:collapse: true

Tool-capable provider requests must preserve explicit tool selection, multi-round execution, and safe public failure boundaries.
```

## Idea branch

This is the whole local intent hierarchy. Use the graph to see the forest; use the
clickable next-level links below it to enter the branch you want.

::::{only} graphviz_available

```{needflow} Tool orchestration idea branch
:engine: graphviz
:direction: down
:root_id: GOAL_TOOL_ORCHESTRATION
:root_direction: incoming
:root_depth: 3
:filter: type in ["goal", "feature", "req", "treq"]
:link_types: derives
:alt: Tool orchestration from goal through requirements and technical requirements
```

::::

::::{only} not graphviz_available
The graph renderer is unavailable in this build. The authoritative Goal, Capability,
Requirement, and Technical requirement cards below preserve the same hierarchy through their relationship
links.
::::

### Enter this branch

```{needlist}
:filter: "'GOAL_TOOL_ORCHESTRATION' in derives"
```

## See this branch as executable behavior

When you want to verify the public behavior at this abstraction level before opening
individual test evidence, use the Living Specifications for this branch. They keep
Gherkin, current execution status, attachments, and the exact requirement provenance
together.

- {ref}`Tool executable behavior <living-specs-area-tools>`

```{feature} Tool selection
:id: FEAT_TOOL_SELECTION
:collapse: true
:derives: GOAL_TOOL_ORCHESTRATION

The normalized tool contract can express an explicit tool choice across provider families.
```

Contracts in this capability:

```{needlist}
:filter: "'FEAT_TOOL_SELECTION' in derives"
```

```{req} Explicit tool choice is honored
:id: REQ_TOOL_CHOICE
:collapse: true
:status: accepted
:revision: 1
:required_evidence: impl;bdd
:derives: FEAT_TOOL_SELECTION

**Statement.** When the caller explicitly selects a named tool, a supported provider route shall request and execute that tool rather than silently choosing another registered tool.

**Rationale.** Explicit tool choice is caller intent; silently substituting another tool can change side effects and invalidate the meaning of the request.

**Verification intent.** Execute a public tool-capable request with multiple registered tools and an explicit selection, then verify the selected tool is the one requested and executed.
```

::::{dropdown} Follow this contract to proof

```{needlist}
:filter: "'REQ_TOOL_CHOICE' in derives or 'REQ_TOOL_CHOICE' in implements or 'REQ_TOOL_CHOICE' in verifies"
```

::::

```{feature} Tool execution
:id: FEAT_TOOL_EXECUTION
:collapse: true
:derives: GOAL_TOOL_ORCHESTRATION

The router can execute local tools across multiple provider turns while enforcing public error and round-limit boundaries.
```

Contracts in this capability:

```{needlist}
:filter: "'FEAT_TOOL_EXECUTION' in derives"
```

```{req} Multi-round tool execution
:id: REQ_MULTI_ROUND_TOOL_EXECUTION
:collapse: true
:status: accepted
:revision: 1
:required_evidence: impl;bdd
:derives: FEAT_TOOL_EXECUTION

**Statement.** Supported provider routes shall be able to execute a multi-step local-tool workflow and feed tool results back into subsequent provider turns until a final response is produced.

**Rationale.** Useful tool orchestration often requires the model to consume one tool result before deciding the next action; a single-round contract would not preserve this workflow.

**Verification intent.** Execute a representative multi-round workflow through the public router and verify each requested tool is executed, its result is returned to the provider turn, and the workflow terminates with the expected final response.
```

::::{dropdown} Follow this contract to proof

```{needlist}
:filter: "'REQ_MULTI_ROUND_TOOL_EXECUTION' in derives or 'REQ_MULTI_ROUND_TOOL_EXECUTION' in implements or 'REQ_MULTI_ROUND_TOOL_EXECUTION' in verifies"
```

::::

```{treq} Tool registry preserves callable contracts
:id: TREQ_TOOL_REGISTRY
:collapse: true
:status: accepted
:revision: 1
:required_evidence: impl;unit
:derives: REQ_MULTI_ROUND_TOOL_EXECUTION

**Statement.** The tool registry shall reject duplicate tool names, derive callable schemas that match Python signatures, parse supported provider tool-call shapes, and execute registered callables consistently.

**Rationale.** The registry is the translation boundary between Python callables and provider tool schemas; ambiguity or schema drift there can invoke the wrong arguments or callable.

**Verification intent.** Directly verify duplicate-name rejection, schema derivation, supported tool-call parsing, and callable execution across representative signatures and provider shapes.
```

::::{dropdown} Follow this contract to proof

```{needlist}
:filter: "'TREQ_TOOL_REGISTRY' in derives or 'TREQ_TOOL_REGISTRY' in implements or 'TREQ_TOOL_REGISTRY' in verifies"
```

::::

```{req} Tool runtime failures are bounded and public
:id: REQ_TOOL_RUNTIME_SAFETY
:collapse: true
:status: accepted
:revision: 1
:required_evidence: impl;bdd
:derives: FEAT_TOOL_EXECUTION

**Statement.** Local tool failures shall surface as the public tool-execution error without leaking sensitive arguments, and tool execution shall stop at the configured maximum round count.

**Rationale.** Tool orchestration runs local code with caller data, so failures need a stable public boundary and execution must remain finite even when the provider repeatedly requests tools.

**Verification intent.** Trigger public tool failures containing sensitive arguments and a workflow that exceeds the configured round limit; verify the public error surface, absence of protected argument values, and bounded execution count.
```

::::{dropdown} Follow this contract to proof

```{needlist}
:filter: "'REQ_TOOL_RUNTIME_SAFETY' in derives or 'REQ_TOOL_RUNTIME_SAFETY' in implements or 'REQ_TOOL_RUNTIME_SAFETY' in verifies"
```

::::

## Continue nearby

Do not jump back to an artifact catalogue when this branch raises a neighboring
question. These are the closest semantic continuations:

- {doc}`Rich input and output <structured_output>` — shared schema and normalized-content concerns.
- {doc}`Data safety <security>` — sensitive tool arguments and failure diagnostics.
- {doc}`Provider portability <providers>` — provider-specific tool-call translation.

To zoom all the way out, return to the {doc}`Intent map <index>`. To investigate a release
blocker instead, open {doc}`Specification health <../specification-health>`.
