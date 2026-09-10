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
:revision: 2
:required_evidence: impl;bdd
:derives: FEAT_PROVIDER_RETRY

**Statement.** Temporary provider failures shall be eligible for retry, while permanent failures shall not be retried as if they were transient.

**Rationale.** Retrying transient failures improves availability, while retrying permanent failures adds latency and cost without increasing the chance of success.

**Verification intent.** Exercise retryable and permanent failures through public provider execution and verify transient failures can recover while permanent failures surface without inappropriate retry.
```

```{treq} Retry classification uses explicit failure semantics
:id: TREQ_PROVIDER_RETRY_CLASSIFICATION
:status: accepted
:revision: 1
:required_evidence: impl;unit
:derives: REQ_PROVIDER_RETRY

**Constraint.** Retry classification shall use explicit status and exception semantics rather than message substrings.

**Rationale.** Message matching is brittle and can classify unrelated exceptions as retryable merely because their text resembles a transient transport failure.

**Verification intent.** Directly verify representative status and exception classifications, including transport exceptions whose messages resemble retryable failures but whose types do not.
```

```{feature} Structured-output recovery
:id: FEAT_STRUCTURED_RECOVERY
:derives: GOAL_RESILIENT_EXECUTION

Invalid structured output can be repaired without allowing unbounded repair attempts or prompts.
```

```{req} Structured output repair is bounded
:id: REQ_STRUCTURED_OUTPUT_REPAIR
:status: accepted
:revision: 2
:required_evidence: impl;bdd
:derives: FEAT_STRUCTURED_RECOVERY

**Statement.** Invalid structured output may be repaired, but repair attempts shall stop at the configured finite limit.

**Rationale.** Repair improves robustness only while its work remains bounded; unbounded retries can turn a malformed response into runaway execution.

**Verification intent.** Exercise successful and exhausted repair through public structured-output behavior and verify repair terminates at the configured attempt limit.
```

```{treq} Repair prompts remain bounded
:id: TREQ_REPAIR_PROMPT_BOUNDS
:status: accepted
:revision: 1
:required_evidence: impl;property
:derives: REQ_STRUCTURED_OUTPUT_REPAIR

**Constraint.** Repair prompts shall bound incorporated invalid output and validation details for arbitrary generated input.

**Rationale.** Even a finite retry loop can consume unbounded prompt space if malformed output and validation detail are copied without limits.

**Verification intent.** Use property-based invalid outputs and validation details to verify the generated repair prompt remains within the intended bounds.
```

## Architecture decisions

The following accepted decision records explain the recovery boundaries behind
these requirements without replacing the requirements themselves.

```{needtable}
:columns: id;title;status;decision_date
:style: table
:filter: type == "adr" and "REQ_PROVIDER_RETRY" in affects
```
