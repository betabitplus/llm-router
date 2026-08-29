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
:revision: 1
:needs_artifacts: impl;bdd
:derives: FEAT_PROVIDER_RETRY

Temporary provider failures must be eligible for retry, while permanent failures must not be retried as if they were transient.
```

```{treq} Retry classification uses explicit failure semantics
:id: TREQ_PROVIDER_RETRY_CLASSIFICATION
:revision: 1
:needs_artifacts: impl;unit
:derives: REQ_PROVIDER_RETRY

Retry classification must distinguish retryable status and transport failures from permanent failures using explicit status and exception types rather than message substrings.
```

```{feature} Structured-output recovery
:id: FEAT_STRUCTURED_RECOVERY
:derives: GOAL_RESILIENT_EXECUTION

Invalid structured output can be repaired without allowing unbounded repair attempts or prompts.
```

```{req} Structured output repair is bounded
:id: REQ_STRUCTURED_OUTPUT_REPAIR
:revision: 1
:needs_artifacts: impl;bdd
:derives: FEAT_STRUCTURED_RECOVERY

Invalid structured output may be repaired, but repair attempts must stop at the configured finite limit.
```

```{treq} Repair prompts remain bounded
:id: TREQ_REPAIR_PROMPT_BOUNDS
:revision: 1
:needs_artifacts: impl;property
:derives: REQ_STRUCTURED_OUTPUT_REPAIR

Repair-prompt construction must cap incorporated invalid output and validation details so prompt size remains bounded for arbitrary generated input.
```
