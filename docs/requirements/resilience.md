# Resilience requirements

{doc}`← Intent map <index>` · {doc}`Whole-system map <maps>` · {doc}`Release health <../specification-health>`

Read this page as one continuous branch of the product idea. Start with the local
**Idea branch** for the big picture. Then inspect only the contracts you care about;
under each Requirement/Technical requirement, **Follow this contract to proof** reveals one downstream hop so
you can drill into implementation or executed verification without opening a global
catalogue.

```{goal} Recover from transient execution failures without unbounded work
:id: GOAL_RESILIENT_EXECUTION
:collapse: true

Recoverable failures should be retried or repaired within explicit limits, while permanent failures should surface promptly.
```

## Idea branch

This is the whole local intent hierarchy. Use the graph to see the forest; use the
clickable next-level links below it to enter the branch you want.

::::{only} graphviz_available

```{needflow} Resilient execution idea branch
:engine: graphviz
:direction: down
:root_id: GOAL_RESILIENT_EXECUTION
:root_direction: incoming
:root_depth: 3
:filter: type in ["goal", "feature", "req", "treq"]
:link_types: derives
:alt: Resilient execution from goal through requirements and technical requirements
```

::::

::::{only} not graphviz_available
The graph renderer is unavailable in this build. The authoritative Goal, Capability,
Requirement, and Technical requirement cards below preserve the same hierarchy through their relationship
links.
::::

### Enter this branch

```{needlist}
:filter: "'GOAL_RESILIENT_EXECUTION' in derives"
```

## See this branch as executable behavior

When you want to verify the public behavior at this abstraction level before opening
individual test evidence, use the Living Specifications for this branch. They keep
Gherkin, current execution status, attachments, and the exact requirement provenance
together.

- {ref}`Resilience executable behavior <living-specs-area-resilience>`

```{feature} Provider retry
:id: FEAT_PROVIDER_RETRY
:collapse: true
:derives: GOAL_RESILIENT_EXECUTION

Provider failures are classified before retry policy is applied.
```

Contracts in this capability:

```{needlist}
:filter: "'FEAT_PROVIDER_RETRY' in derives"
```

```{req} Retry only temporary provider failures
:id: REQ_PROVIDER_RETRY
:collapse: true
:status: accepted
:revision: 2
:required_evidence: impl;bdd
:derives: FEAT_PROVIDER_RETRY

**Statement.** Temporary provider failures shall be eligible for retry, while permanent failures shall not be retried as if they were transient.

**Rationale.** Retrying transient failures improves availability, while retrying permanent failures adds latency and cost without increasing the chance of success.

**Verification intent.** Exercise retryable and permanent failures through public provider execution and verify transient failures can recover while permanent failures surface without inappropriate retry.
```

::::{dropdown} Follow this contract to proof

```{needlist}
:filter: "'REQ_PROVIDER_RETRY' in derives or 'REQ_PROVIDER_RETRY' in implements or 'REQ_PROVIDER_RETRY' in verifies"
```

::::

```{treq} Retry classification uses explicit failure semantics
:id: TREQ_PROVIDER_RETRY_CLASSIFICATION
:collapse: true
:status: accepted
:revision: 1
:required_evidence: impl;unit
:derives: REQ_PROVIDER_RETRY

**Statement.** Retry classification shall use explicit status and exception semantics rather than message substrings.

**Rationale.** Message matching is brittle and can classify unrelated exceptions as retryable merely because their text resembles a transient transport failure.

**Verification intent.** Directly verify representative status and exception classifications, including transport exceptions whose messages resemble retryable failures but whose types do not.
```

::::{dropdown} Follow this contract to proof

```{needlist}
:filter: "'TREQ_PROVIDER_RETRY_CLASSIFICATION' in derives or 'TREQ_PROVIDER_RETRY_CLASSIFICATION' in implements or 'TREQ_PROVIDER_RETRY_CLASSIFICATION' in verifies"
```

::::

```{feature} Structured-output recovery
:id: FEAT_STRUCTURED_RECOVERY
:collapse: true
:derives: GOAL_RESILIENT_EXECUTION

Invalid structured output can be repaired without allowing unbounded repair attempts or prompts.
```

Contracts in this capability:

```{needlist}
:filter: "'FEAT_STRUCTURED_RECOVERY' in derives"
```

```{req} Structured output repair is bounded
:id: REQ_STRUCTURED_OUTPUT_REPAIR
:collapse: true
:status: accepted
:revision: 2
:required_evidence: impl;bdd
:derives: FEAT_STRUCTURED_RECOVERY

**Statement.** Invalid structured output may be repaired, but repair attempts shall stop at the configured finite limit.

**Rationale.** Repair improves robustness only while its work remains bounded; unbounded retries can turn a malformed response into runaway execution.

**Verification intent.** Exercise successful and exhausted repair through public structured-output behavior and verify repair terminates at the configured attempt limit.
```

::::{dropdown} Follow this contract to proof

```{needlist}
:filter: "'REQ_STRUCTURED_OUTPUT_REPAIR' in derives or 'REQ_STRUCTURED_OUTPUT_REPAIR' in implements or 'REQ_STRUCTURED_OUTPUT_REPAIR' in verifies"
```

::::

```{treq} Repair prompts remain bounded
:id: TREQ_REPAIR_PROMPT_BOUNDS
:collapse: true
:status: accepted
:revision: 1
:required_evidence: impl;property
:derives: REQ_STRUCTURED_OUTPUT_REPAIR

**Statement.** Repair prompts shall bound incorporated invalid output and validation details for arbitrary generated input.

**Rationale.** Even a finite retry loop can consume unbounded prompt space if malformed output and validation detail are copied without limits.

**Verification intent.** Use property-based invalid outputs and validation details to verify the generated repair prompt remains within the intended bounds.
```

::::{dropdown} Follow this contract to proof

```{needlist}
:filter: "'TREQ_REPAIR_PROMPT_BOUNDS' in derives or 'TREQ_REPAIR_PROMPT_BOUNDS' in implements or 'TREQ_REPAIR_PROMPT_BOUNDS' in verifies"
```

::::

## Architecture decisions

The following accepted decision records explain the recovery boundaries behind
these requirements without replacing the requirements themselves.

```{needlist}
:filter: type == "adr" and "REQ_PROVIDER_RETRY" in affects
```

## Continue nearby

Do not jump back to an artifact catalogue when this branch raises a neighboring
question. These are the closest semantic continuations:

- {doc}`Routing reliability <routing>` — what happens after same-route recovery is exhausted.
- {doc}`Provider portability <providers>` — where normalized provider failures originate.
- {doc}`Rich input and output <structured_output>` — the structured-output contract being repaired.

To zoom all the way out, return to the {doc}`Intent map <index>`. To investigate a release
blocker instead, open {doc}`Specification health <../specification-health>`.
