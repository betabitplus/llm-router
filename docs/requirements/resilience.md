# Resilience requirements

```{goal} Recover from transient execution failures without unbounded work
:id: GOAL_RESILIENT_EXECUTION

Recoverable failures should be retried or repaired within explicit limits, while permanent failures should surface promptly.
```

```{feature} Provider retry
:id: FEAT_PROVIDER_RETRY
:derives: GOAL_RESILIENT_EXECUTION

Provider failures are classified before retry policy is applied.
```

```{req} Retry only temporary provider failures
:id: REQ_PROVIDER_RETRY
:status: accepted
:revision: 1
:required_evidence: impl;bdd;unit
:derives: FEAT_PROVIDER_RETRY

**Statement.** Temporary provider failures shall be eligible for retry, while permanent failures shall not be retried as if they were transient. Classification shall use explicit status and exception semantics rather than message substrings.

**Rationale.** Retrying transient failures improves availability, but retrying permanent failures adds latency and cost while brittle message matching can misclassify unrelated exceptions.

**Verification intent.** Exercise retryable and permanent failures through public provider execution and directly verify the status/exception classification boundary across representative cases.
```

```{feature} Structured-output recovery
:id: FEAT_STRUCTURED_RECOVERY
:derives: GOAL_RESILIENT_EXECUTION

Invalid structured output can be repaired without allowing unbounded repair attempts or prompts.
```

```{req} Structured output repair is bounded
:id: REQ_STRUCTURED_OUTPUT_REPAIR
:status: accepted
:revision: 1
:required_evidence: impl;bdd;property
:derives: FEAT_STRUCTURED_RECOVERY

**Statement.** Invalid structured output may be repaired, but repair attempts shall stop at the configured finite limit. Repair prompts shall bound incorporated invalid output and validation details for arbitrary generated input.

**Rationale.** Repair improves robustness only while its work and prompt growth remain predictable; unbounded retries or echoed invalid content can turn a malformed response into runaway execution.

**Verification intent.** Exercise successful and exhausted repair through public structured-output behavior and use property-based inputs to verify prompt and attempt bounds over arbitrary invalid output and validation details.
```

## Architecture decisions

The following accepted decision records explain the recovery boundaries behind
these requirements without replacing the requirements themselves.

```{needtable}
:columns: id;title;status;decision_date
:style: table
:filter: type == "adr" and "REQ_PROVIDER_RETRY" in affects
```
